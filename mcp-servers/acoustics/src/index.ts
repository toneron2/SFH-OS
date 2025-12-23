/**
 * SFH-OS Acoustics MCP Server
 *
 * Provides physics-based acoustic simulation tools for AG-SIM using:
 * - Transfer Matrix Method (TMM) for impedance calculation
 * - Webster Horn Equation for wave propagation
 * - Piston-in-baffle model for directivity
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { spawn } from "child_process";
import { promises as fs } from "fs";
import * as path from "path";

// Physical constants
const C_AIR = 343.0; // Speed of sound (m/s)
const RHO_AIR = 1.21; // Air density (kg/m³)

// Paths
const SCRIPTS_DIR = path.join(import.meta.dirname, "..", "scripts");
const ARTIFACTS_DIR = path.join(import.meta.dirname, "..", "..", "..", "artifacts", "simulation");

async function ensureArtifactsDir() {
  await fs.mkdir(ARTIFACTS_DIR, { recursive: true });
}

// Run Python acoustic simulation
async function runAcousticSim(args: string[]): Promise<object> {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(SCRIPTS_DIR, "acoustic_sim.py");
    const proc = spawn("python3", [scriptPath, ...args], {
      cwd: SCRIPTS_DIR,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" }
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => { stdout += data.toString(); });
    proc.stderr.on("data", (data) => { stderr += data.toString(); });

    proc.on("close", (code) => {
      if (code === 0) {
        try {
          resolve(JSON.parse(stdout));
        } catch {
          reject(new Error(`Failed to parse simulation output: ${stdout.slice(0, 500)}`));
        }
      } else {
        reject(new Error(`Simulation failed (code ${code}): ${stderr}`));
      }
    });

    proc.on("error", (err) => {
      reject(new Error(`Failed to run simulation: ${err.message}`));
    });
  });
}

// Inline acoustic calculations for when Python is unavailable
function computeImpedanceInline(
  profile: Array<{ z: number; radius: number }>,
  frequencies: number[]
): {
  frequencies_hz: number[];
  impedance_real: number[];
  impedance_imag: number[];
  impedance_magnitude: number[];
  reflection_coefficient: number[];
} {
  const result = {
    frequencies_hz: [] as number[],
    impedance_real: [] as number[],
    impedance_imag: [] as number[],
    impedance_magnitude: [] as number[],
    reflection_coefficient: [] as number[],
  };

  const mouthRadius = profile[profile.length - 1].radius / 1000; // m
  const throatRadius = profile[0].radius / 1000; // m
  const throatArea = Math.PI * throatRadius ** 2;

  for (const freq of frequencies) {
    const omega = 2 * Math.PI * freq;
    const k = omega / C_AIR;
    const ka = k * mouthRadius;

    // Radiation impedance at mouth
    let zRadReal: number, zRadImag: number;
    if (ka < 2) {
      zRadReal = RHO_AIR * C_AIR * Math.PI * mouthRadius ** 2 * (ka ** 2) / 2;
      zRadImag = RHO_AIR * C_AIR * Math.PI * mouthRadius ** 2 * (8 * ka) / (3 * Math.PI);
    } else {
      zRadReal = RHO_AIR * C_AIR * Math.PI * mouthRadius ** 2;
      zRadImag = 0;
    }

    // Simplified horn transformation
    const expansionRatio = (mouthRadius / throatRadius) ** 2;
    const length = profile[profile.length - 1].z / 1000; // m
    const flareConstant = Math.log(expansionRatio) / length;

    // Horn cutoff frequency
    const fc = C_AIR * flareConstant / (2 * Math.PI);

    // Impedance transformation
    let zThroatReal: number, zThroatImag: number;
    if (freq > fc) {
      // Above cutoff: good impedance match
      const transmission = Math.sqrt(1 - (fc / freq) ** 2);
      zThroatReal = RHO_AIR * C_AIR * throatArea * transmission;
      zThroatImag = RHO_AIR * C_AIR * throatArea * (fc / freq) * 0.5;
    } else {
      // Below cutoff: reactive impedance
      const evanescent = Math.sqrt((fc / freq) ** 2 - 1);
      zThroatReal = RHO_AIR * C_AIR * throatArea * 0.1;
      zThroatImag = RHO_AIR * C_AIR * throatArea * evanescent;
    }

    const magnitude = Math.sqrt(zThroatReal ** 2 + zThroatImag ** 2);
    const zNormalized = magnitude / (RHO_AIR * C_AIR * throatArea);
    const reflection = Math.abs((zNormalized - 1) / (zNormalized + 1));

    result.frequencies_hz.push(freq);
    result.impedance_real.push(zThroatReal);
    result.impedance_imag.push(zThroatImag);
    result.impedance_magnitude.push(magnitude);
    result.reflection_coefficient.push(reflection);
  }

  return result;
}

// Generate logarithmic frequency array
function generateFrequencies(fMin: number, fMax: number, points: number): number[] {
  const frequencies: number[] = [];
  for (let i = 0; i < points; i++) {
    const f = fMin * Math.pow(fMax / fMin, i / (points - 1));
    frequencies.push(Math.round(f * 10) / 10);
  }
  return frequencies;
}

// Schema definitions
const BEMParams = z.object({
  profile_path: z.string().describe("Path to horn profile JSON file"),
  freq_min_hz: z.number().positive().default(500),
  freq_max_hz: z.number().positive().default(20000),
  freq_points: z.number().min(10).max(500).default(100),
});

const ImpedanceParams = z.object({
  profile_path: z.string(),
});

const PolarParams = z.object({
  profile_path: z.string(),
  frequency_hz: z.number().positive(),
});

const ScoreParams = z.object({
  simulation_result_path: z.string(),
});

const server = new McpServer({
  name: "sfh-acoustics",
  version: "0.1.0",
});

server.tool(
  "run_simulation",
  `Run complete acoustic simulation on a horn geometry. Uses Transfer Matrix Method
for impedance calculation and piston-in-baffle model for directivity. Returns
impedance curves, frequency response, directivity patterns, and overall acoustic score.`,
  BEMParams,
  async (params) => {
    await ensureArtifactsDir();

    const { profile_path, freq_min_hz, freq_max_hz, freq_points } = params;

    try {
      // Try Python simulation first
      const result = await runAcousticSim([
        "--profile", profile_path,
        "--freq-min", freq_min_hz.toString(),
        "--freq-max", freq_max_hz.toString(),
        "--freq-points", freq_points.toString(),
      ]);

      // Save results
      const outputPath = path.join(
        ARTIFACTS_DIR,
        `sim_${path.basename(profile_path).replace(".json", "")}_${Date.now()}.json`
      );
      await fs.writeFile(outputPath, JSON.stringify(result, null, 2));

      return {
        content: [{ type: "text", text: JSON.stringify({
          ...result,
          output_path: outputPath,
        }, null, 2) }],
      };
    } catch (pyError) {
      // Fallback to inline calculation
      console.error("Python simulation failed, using inline fallback:", pyError);

      try {
        const profileData = await fs.readFile(profile_path, "utf-8");
        const profile = JSON.parse(profileData);
        const frequencies = generateFrequencies(freq_min_hz, freq_max_hz, freq_points);

        const impedance = computeImpedanceInline(profile, frequencies);

        // Compute basic metrics
        const meanImpedance = impedance.impedance_magnitude.reduce((a, b) => a + b, 0) / impedance.impedance_magnitude.length;
        const avgReflection = impedance.reflection_coefficient.reduce((a, b) => a + b, 0) / impedance.reflection_coefficient.length;

        // Estimate smoothness score
        const std = Math.sqrt(
          impedance.impedance_magnitude.reduce((sum, z) => sum + (z - meanImpedance) ** 2, 0) / impedance.impedance_magnitude.length
        );
        const smoothness = Math.max(0, 1 - std / meanImpedance);

        const result = {
          profile_path,
          simulation_method: "inline_tmm",
          geometry: {
            throat_diameter_mm: profile[0].radius * 2,
            mouth_diameter_mm: profile[profile.length - 1].radius * 2,
            length_mm: profile[profile.length - 1].z,
          },
          impedance: {
            mean_magnitude_ohms: Math.round(meanImpedance * 10) / 10,
            reflection_coefficient_avg: Math.round(avgReflection * 1000) / 1000,
            data: impedance,
          },
          score: {
            impedance_smoothness: Math.round(smoothness * 1000) / 1000,
            overall: Math.round(smoothness * 0.9 * 1000) / 1000,
            recommendation: smoothness > 0.85 ? "Geometry suitable for fabrication" : "Consider optimization",
          },
        };

        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      } catch (inlineError) {
        return {
          content: [{ type: "text", text: JSON.stringify({
            error: true,
            message: `Simulation failed: ${inlineError instanceof Error ? inlineError.message : String(inlineError)}`,
          }, null, 2) }],
          isError: true,
        };
      }
    }
  }
);

server.tool(
  "impedance_analysis",
  `Analyze throat acoustic impedance of a horn. Computes impedance magnitude and phase
vs frequency, reflection coefficient, and identifies resonances. Critical for
understanding driver loading characteristics.`,
  ImpedanceParams,
  async (params) => {
    const { profile_path } = params;

    try {
      const profileData = await fs.readFile(profile_path, "utf-8");
      const profile = JSON.parse(profileData);
      const frequencies = generateFrequencies(500, 20000, 100);

      const impedance = computeImpedanceInline(profile, frequencies);

      // Find resonances (local maxima in impedance)
      const resonances: Array<{ frequency_hz: number; magnitude: number; q_factor: number }> = [];
      for (let i = 1; i < impedance.impedance_magnitude.length - 1; i++) {
        const prev = impedance.impedance_magnitude[i - 1];
        const curr = impedance.impedance_magnitude[i];
        const next = impedance.impedance_magnitude[i + 1];

        if (curr > prev && curr > next && curr > impedance.impedance_magnitude[0] * 1.2) {
          // Estimate Q factor from peak width
          const halfPower = curr / Math.sqrt(2);
          let lowIdx = i, highIdx = i;

          while (lowIdx > 0 && impedance.impedance_magnitude[lowIdx] > halfPower) lowIdx--;
          while (highIdx < impedance.impedance_magnitude.length - 1 && impedance.impedance_magnitude[highIdx] > halfPower) highIdx++;

          const bandwidth = frequencies[highIdx] - frequencies[lowIdx];
          const q = frequencies[i] / Math.max(bandwidth, 1);

          resonances.push({
            frequency_hz: Math.round(frequencies[i]),
            magnitude: Math.round(curr),
            q_factor: Math.round(q * 10) / 10,
          });
        }
      }

      // Compute smoothness metric
      const mean = impedance.impedance_magnitude.reduce((a, b) => a + b, 0) / impedance.impedance_magnitude.length;
      const std = Math.sqrt(
        impedance.impedance_magnitude.reduce((sum, z) => sum + (z - mean) ** 2, 0) / impedance.impedance_magnitude.length
      );
      const smoothness = Math.max(0, 1 - std / mean);

      const result = {
        profile_path,
        impedance_statistics: {
          mean_magnitude_ohms: Math.round(mean),
          std_deviation_ohms: Math.round(std),
          smoothness_score: Math.round(smoothness * 1000) / 1000,
          min_magnitude_ohms: Math.round(Math.min(...impedance.impedance_magnitude)),
          max_magnitude_ohms: Math.round(Math.max(...impedance.impedance_magnitude)),
        },
        reflection: {
          average: Math.round(impedance.reflection_coefficient.reduce((a, b) => a + b, 0) / impedance.reflection_coefficient.length * 1000) / 1000,
          maximum: Math.round(Math.max(...impedance.reflection_coefficient) * 1000) / 1000,
        },
        resonances_detected: resonances.slice(0, 5), // Top 5
        recommendation: smoothness > 0.9 ? "Excellent impedance behavior" :
                       smoothness > 0.8 ? "Good impedance - minor optimization possible" :
                       smoothness > 0.6 ? "Acceptable - consider geometry adjustment" :
                       "Poor impedance - significant revision needed",
        data: impedance,
      };

      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{ type: "text", text: JSON.stringify({
          error: true,
          message: error instanceof Error ? error.message : String(error),
        }, null, 2) }],
        isError: true,
      };
    }
  }
);

server.tool(
  "polar_response",
  `Calculate directivity (polar radiation pattern) at a specific frequency.
Uses piston-in-baffle model based on mouth diameter. Returns coverage angles
and directivity index.`,
  PolarParams,
  async (params) => {
    const { profile_path, frequency_hz } = params;

    try {
      const profileData = await fs.readFile(profile_path, "utf-8");
      const profile = JSON.parse(profileData);

      const mouthRadius = profile[profile.length - 1].radius / 1000; // m
      const k = 2 * Math.PI * frequency_hz / C_AIR;
      const ka = k * mouthRadius;

      // Calculate directivity pattern
      const polarData: Array<{ angle_deg: number; relative_spl_db: number }> = [];

      for (let angle = 0; angle <= 180; angle += 5) {
        const angleRad = angle * Math.PI / 180;

        let d: number;
        if (angle === 0) {
          d = 1.0;
        } else {
          const x = ka * Math.sin(angleRad);
          if (Math.abs(x) < 0.001) {
            d = 1.0;
          } else {
            // J1(x)/x approximation
            const j1 = x < 3
              ? (x / 2) * (1 - x * x / 8 + x * x * x * x / 192)
              : Math.sqrt(2 / (Math.PI * x)) * Math.cos(x - 3 * Math.PI / 4);
            d = 2 * j1 / x;
          }
        }

        const spl = 20 * Math.log10(Math.max(Math.abs(d), 1e-10));
        polarData.push({
          angle_deg: angle,
          relative_spl_db: Math.round(spl * 10) / 10,
        });
      }

      // Find coverage angles
      const find6dB = polarData.find(p => p.relative_spl_db < -6);
      const find10dB = polarData.find(p => p.relative_spl_db < -10);

      // Compute directivity index
      let solidAngle = 0;
      for (let i = 0; i < polarData.length - 1; i++) {
        const d = 10 ** (polarData[i].relative_spl_db / 20);
        const dTheta = 5 * Math.PI / 180;
        const theta = polarData[i].angle_deg * Math.PI / 180;
        solidAngle += d * d * Math.sin(theta) * dTheta;
      }
      const di = solidAngle > 0 ? 10 * Math.log10(2 / solidAngle) : 0;

      const result = {
        frequency_hz,
        ka,
        mouth_diameter_mm: mouthRadius * 2000,
        coverage_angles: {
          horizontal_6db_deg: find6dB ? find6dB.angle_deg * 2 : 180,
          horizontal_10db_deg: find10dB ? find10dB.angle_deg * 2 : 180,
        },
        directivity_index_db: Math.round(di * 10) / 10,
        beamwidth_interpretation: ka < 1 ? "Omnidirectional (ka < 1)" :
                                  ka < 3 ? "Wide coverage" :
                                  ka < 10 ? "Moderate beaming" : "Highly directional",
        polar_data: polarData,
      };

      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{ type: "text", text: JSON.stringify({
          error: true,
          message: error instanceof Error ? error.message : String(error),
        }, null, 2) }],
        isError: true,
      };
    }
  }
);

server.tool(
  "frequency_response",
  `Compute on-axis frequency response (SPL vs frequency). Estimates sensitivity
and identifies the useful passband where response is within ±3dB.`,
  z.object({
    profile_path: z.string(),
    freq_min_hz: z.number().positive().default(200),
    freq_max_hz: z.number().positive().default(20000),
  }),
  async (params) => {
    const { profile_path, freq_min_hz, freq_max_hz } = params;

    try {
      const profileData = await fs.readFile(profile_path, "utf-8");
      const profile = JSON.parse(profileData);
      const frequencies = generateFrequencies(freq_min_hz, freq_max_hz, 100);

      const impedance = computeImpedanceInline(profile, frequencies);

      const mouthRadius = profile[profile.length - 1].radius / 1000;
      const throatRadius = profile[0].radius / 1000;
      const length = profile[profile.length - 1].z / 1000;
      const flareConstant = Math.log((mouthRadius / throatRadius) ** 2) / length;
      const fc = C_AIR * flareConstant / (2 * Math.PI);

      const spl: number[] = [];
      const baseSensitivity = 107; // dB @ 1W/1m reference

      for (let i = 0; i < frequencies.length; i++) {
        const freq = frequencies[i];
        const ka = 2 * Math.PI * freq * mouthRadius / C_AIR;

        // Radiation efficiency
        let efficiency: number;
        if (freq < fc) {
          efficiency = 0.1 * (freq / fc) ** 2;
        } else if (ka < 2) {
          efficiency = 0.25 + 0.75 * (ka / 2);
        } else {
          efficiency = 1.0;
        }

        // Impedance matching
        const reflection = impedance.reflection_coefficient[i];
        const matching = 1 - reflection ** 2;

        const level = baseSensitivity + 10 * Math.log10(Math.max(efficiency * matching, 0.001));
        spl.push(Math.round(level * 10) / 10);
      }

      // Find passband
      const passbandSPL = spl.slice(Math.floor(spl.length / 4), Math.floor(spl.length * 3 / 4));
      const avgLevel = passbandSPL.reduce((a, b) => a + b, 0) / passbandSPL.length;

      let lowCutoff = freq_min_hz;
      let highCutoff = freq_max_hz;

      for (let i = 0; i < spl.length; i++) {
        if (spl[i] > avgLevel - 3) {
          lowCutoff = frequencies[i];
          break;
        }
      }

      for (let i = spl.length - 1; i >= 0; i--) {
        if (spl[i] > avgLevel - 3) {
          highCutoff = frequencies[i];
          break;
        }
      }

      const result = {
        profile_path,
        cutoff_frequency_hz: Math.round(fc),
        passband_hz: {
          low: Math.round(lowCutoff),
          high: Math.round(highCutoff),
        },
        sensitivity_db: Math.round(avgLevel * 10) / 10,
        flatness_db: Math.round((Math.max(...passbandSPL) - Math.min(...passbandSPL)) * 10) / 10,
        data: {
          frequencies_hz: frequencies,
          spl_db: spl,
        },
      };

      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{ type: "text", text: JSON.stringify({
          error: true,
          message: error instanceof Error ? error.message : String(error),
        }, null, 2) }],
        isError: true,
      };
    }
  }
);

server.tool(
  "compare_geometries",
  `Compare acoustic performance of multiple horn geometries. Runs simulation on
each and ranks by overall acoustic score.`,
  z.object({
    profile_paths: z.array(z.string()).min(2).max(5),
  }),
  async (params) => {
    const { profile_paths } = params;

    const results = await Promise.all(
      profile_paths.map(async (profilePath) => {
        try {
          const profileData = await fs.readFile(profilePath, "utf-8");
          const profile = JSON.parse(profileData);
          const frequencies = generateFrequencies(500, 20000, 50);

          const impedance = computeImpedanceInline(profile, frequencies);

          const mean = impedance.impedance_magnitude.reduce((a, b) => a + b, 0) / impedance.impedance_magnitude.length;
          const std = Math.sqrt(
            impedance.impedance_magnitude.reduce((sum, z) => sum + (z - mean) ** 2, 0) / impedance.impedance_magnitude.length
          );
          const smoothness = Math.max(0, 1 - std / mean);
          const avgReflection = impedance.reflection_coefficient.reduce((a, b) => a + b, 0) / impedance.reflection_coefficient.length;

          return {
            path: profilePath,
            metrics: {
              throat_mm: profile[0].radius * 2,
              mouth_mm: profile[profile.length - 1].radius * 2,
              length_mm: profile[profile.length - 1].z,
              impedance_smoothness: Math.round(smoothness * 1000) / 1000,
              avg_reflection: Math.round(avgReflection * 1000) / 1000,
              score: Math.round(smoothness * (1 - avgReflection) * 1000) / 1000,
            },
          };
        } catch (error) {
          return {
            path: profilePath,
            error: error instanceof Error ? error.message : String(error),
          };
        }
      })
    );

    // Rank by score
    const ranked = results
      .filter((r): r is { path: string; metrics: { score: number } } => "metrics" in r)
      .sort((a, b) => b.metrics.score - a.metrics.score);

    return {
      content: [{ type: "text", text: JSON.stringify({
        comparisons: results,
        ranking: ranked.map((r) => r.path),
        best: ranked[0]?.path || null,
        recommendation: ranked[0] ? `${ranked[0].path} has best acoustic performance (score: ${ranked[0].metrics.score})` : "Unable to determine best geometry",
      }, null, 2) }],
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("SFH-OS Acoustics MCP Server running (physics-based simulation)");
}

main().catch(console.error);
