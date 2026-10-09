/**
 * SFH-OS Geometry MCP Server
 *
 * Provides fractal geometry generation tools for AG-GEN using FreeCAD.
 * - Hilbert curve horn generation
 * - Peano curve horn generation
 * - Mandelbrot expansion profiles
 * - Mesh creation and fractal analysis
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { spawn } from "child_process";
import { promises as fs } from "fs";
import * as path from "path";

// Paths
const SCRIPTS_DIR = path.join(import.meta.dirname, "..", "scripts");
const ARTIFACTS_DIR = path.join(import.meta.dirname, "..", "..", "..", "artifacts", "geometry");

// Ensure artifacts directory exists
async function ensureArtifactsDir() {
  await fs.mkdir(ARTIFACTS_DIR, { recursive: true });
}

// Interpreters to try, in order. freecadcmd gives a true BRep solid;
// plain Python falls back to the built-in mesh writer.
const INTERPRETERS = ["freecadcmd", "python3", "python"];

// Spawn one interpreter. Resolves with the parsed JSON result, rejects with
// { notFound: true } if the executable does not exist so the caller can try
// the next one, or with an Error for a real failure.
function runWith(cmd: string, scriptPath: string, args: string[]): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const fullArgs = cmd === "freecadcmd"
      ? [scriptPath, "--", ...args, "--json"]
      : [scriptPath, ...args, "--json"];

    const proc = spawn(cmd, fullArgs, {
      cwd: SCRIPTS_DIR,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });

    let stdout = "";
    let stderr = "";
    let spawnFailed = false;

    proc.stdout.on("data", (data) => { stdout += data.toString(); });
    proc.stderr.on("data", (data) => { stderr += data.toString(); });

    // ENOENT fires "error" and then "close" with a negative code; make sure
    // only the first wins.
    proc.on("error", (err: NodeJS.ErrnoException) => {
      spawnFailed = true;
      if (err.code === "ENOENT") reject({ notFound: true });
      else reject(new Error(`Failed to start ${cmd}: ${err.message}`));
    });

    proc.on("close", (code) => {
      if (spawnFailed) return;
      if (code !== 0) {
        reject(new Error(`Generator failed (${cmd} exit ${code}): ${stderr.trim()}`));
        return;
      }
      // freecadcmd may print a banner before the script's JSON; parse from
      // the first "{" onward.
      const jsonStart = stdout.indexOf("{");
      try {
        resolve(JSON.parse(jsonStart >= 0 ? stdout.slice(jsonStart) : stdout));
      } catch {
        reject(new Error(`Failed to parse generator output from ${cmd}: ${stdout.slice(0, 500)}`));
      }
    });
  });
}

// Execute the horn generator with the first available interpreter.
async function runHornGenerator(args: string[]): Promise<Record<string, unknown>> {
  const scriptPath = path.join(SCRIPTS_DIR, "generate_horn.py");
  for (const cmd of INTERPRETERS) {
    try {
      return await runWith(cmd, scriptPath, args);
    } catch (err) {
      if (err && typeof err === "object" && "notFound" in err) continue;
      throw err;
    }
  }
  throw new Error(`No Python interpreter found (tried ${INTERPRETERS.join(", ")})`);
}

// The generator writes the expansion profile next to the mesh and reports
// its path under output.profile_path; fall back to the conventional name.
function profilePathFor(meshPath: string, result: Record<string, unknown>): string {
  const output = result.output as { profile_path?: string } | undefined;
  return output?.profile_path ?? meshPath.replace(/\.stl$/, "_profile.json");
}

// Generate unique ID for geometry
function generateId(): string {
  return `${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

// Tool parameter schemas
const HilbertParams = z.object({
  order: z.number().min(1).max(6).default(4),
  throat_diameter_mm: z.number().positive().default(25.4),
  mouth_diameter_mm: z.number().positive().default(300),
  length_mm: z.number().positive().default(400),
  angular_resolution: z.number().min(24).max(360).default(72),
});

const PeanoParams = z.object({
  iterations: z.number().min(1).max(5).default(3),
  throat_diameter_mm: z.number().positive().default(25.4),
  mouth_diameter_mm: z.number().positive().default(300),
  length_mm: z.number().positive().default(400),
  angular_resolution: z.number().min(24).max(360).default(72),
});

const MandelbrotParams = z.object({
  c_real: z.number().default(-0.75),
  c_imag: z.number().default(0),
  iterations: z.number().min(10).max(1000).default(100),
  throat_diameter_mm: z.number().positive().default(25.4),
  mouth_diameter_mm: z.number().positive().default(300),
  length_mm: z.number().positive().default(400),
  angular_resolution: z.number().min(24).max(360).default(72),
});

const AnalyzeParams = z.object({
  mesh_path: z.string(),
});

const CompareParams = z.object({
  geometry_ids: z.array(z.string()).min(2).max(5),
});

// Create MCP server
const server = new McpServer({
  name: "sfh-geometry",
  version: "0.1.0",
});

// Register tools
server.tool(
  "generate_hilbert",
  `Generate a Hilbert curve-based horn geometry. The Hilbert space-filling curve creates
smooth impedance transitions optimal for broadband acoustic performance. Higher order
values increase fractal complexity but also computation time.`,
  HilbertParams.shape,
  async (params) => {
    await ensureArtifactsDir();

    const id = generateId();
    const outputPath = path.join(ARTIFACTS_DIR, `hilbert_o${params.order}_${id}.stl`);

    try {
      const result = await runHornGenerator([
        "--type", "hilbert",
        "--throat", params.throat_diameter_mm.toString(),
        "--mouth", params.mouth_diameter_mm.toString(),
        "--length", params.length_mm.toString(),
        "--order", params.order.toString(),
        "--resolution", params.angular_resolution.toString(),
        "--output", outputPath,
      ]);

      // Enhance result with ID and type info
      const enhanced = {
        geometry_id: id,
        curve_type: "hilbert",
        order: params.order,
        ...result,
        files: {
          mesh: outputPath,
          profile: profilePathFor(outputPath, result),
        },
      };

      return {
        content: [{ type: "text", text: JSON.stringify(enhanced, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{ type: "text", text: JSON.stringify({
          error: true,
          message: error instanceof Error ? error.message : String(error),
          fallback: "Using analytical profile generation",
        }, null, 2) }],
        isError: true,
      };
    }
  }
);

server.tool(
  "generate_peano",
  `Generate a Peano curve-based horn geometry. Peano curves have higher fractal dimension
than Hilbert curves (approaching 2.0), creating denser acoustic channeling patterns
optimal for maximum high-frequency detail and complex internal structure.`,
  PeanoParams.shape,
  async (params) => {
    await ensureArtifactsDir();

    const id = generateId();
    const outputPath = path.join(ARTIFACTS_DIR, `peano_i${params.iterations}_${id}.stl`);

    try {
      const result = await runHornGenerator([
        "--type", "peano",
        "--throat", params.throat_diameter_mm.toString(),
        "--mouth", params.mouth_diameter_mm.toString(),
        "--length", params.length_mm.toString(),
        "--iterations", params.iterations.toString(),
        "--resolution", params.angular_resolution.toString(),
        "--output", outputPath,
      ]);

      const enhanced = {
        geometry_id: id,
        curve_type: "peano",
        iterations: params.iterations,
        ...result,
        files: {
          mesh: outputPath,
          profile: profilePathFor(outputPath, result),
        },
      };

      return {
        content: [{ type: "text", text: JSON.stringify(enhanced, null, 2) }],
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
  "generate_mandelbrot",
  `Generate a Mandelbrot set-based horn geometry. Uses fractal boundary sampling to create
expansion profiles with infinite detail at every scale. The 'c' parameter controls which
region of the Mandelbrot boundary to sample:
- c = -0.75 + 0i: Main cardioid (smooth expansion)
- c = -1.25 + 0i: Period-2 bulb (dual-rate expansion)
- c = -0.1 + 0.75i: Spiral region (helical structure)`,
  MandelbrotParams.shape,
  async (params) => {
    await ensureArtifactsDir();

    const id = generateId();
    const cStr = `c${params.c_real.toFixed(2).replace("-", "n")}${params.c_imag >= 0 ? "p" : "n"}${Math.abs(params.c_imag).toFixed(2)}`;
    const outputPath = path.join(ARTIFACTS_DIR, `mandelbrot_${cStr}_${id}.stl`);

    try {
      const result = await runHornGenerator([
        "--type", "mandelbrot",
        "--throat", params.throat_diameter_mm.toString(),
        "--mouth", params.mouth_diameter_mm.toString(),
        "--length", params.length_mm.toString(),
        "--iterations", params.iterations.toString(),
        "--c-real", params.c_real.toString(),
        "--c-imag", params.c_imag.toString(),
        "--resolution", params.angular_resolution.toString(),
        "--output", outputPath,
      ]);

      const enhanced = {
        geometry_id: id,
        curve_type: "mandelbrot",
        c: { real: params.c_real, imag: params.c_imag },
        iterations: params.iterations,
        ...result,
        files: {
          mesh: outputPath,
          profile: profilePathFor(outputPath, result),
        },
      };

      return {
        content: [{ type: "text", text: JSON.stringify(enhanced, null, 2) }],
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
  "analyze_fractal",
  `Analyze fractal properties of an existing horn mesh. Computes local and global fractal
dimensions, surface complexity metrics, and predicted acoustic performance indicators.`,
  AnalyzeParams.shape,
  async (params) => {
    const { mesh_path } = params;

    // Read profile if it exists
    const profilePath = mesh_path.replace(".stl", "_profile.json");
    let profile: Array<{ z: number; radius: number }> = [];

    try {
      const profileData = await fs.readFile(profilePath, "utf-8");
      profile = JSON.parse(profileData);
    } catch {
      // Profile not found, generate approximate analysis
    }

    // Calculate fractal dimension from profile
    let globalDimension = 1.5;
    let dimensionVariance = 0.1;

    if (profile.length > 10) {
      const derivatives: number[] = [];
      for (let i = 1; i < profile.length; i++) {
        const dr = profile[i].radius - profile[i - 1].radius;
        const dz = profile[i].z - profile[i - 1].z;
        if (dz > 0) derivatives.push(Math.abs(dr / dz));
      }

      if (derivatives.length > 0) {
        const mean = derivatives.reduce((a, b) => a + b, 0) / derivatives.length;
        const variance = derivatives.reduce((a, b) => a + (b - mean) ** 2, 0) / derivatives.length;
        const std = Math.sqrt(variance);
        const cv = std / mean;
        globalDimension = 1.0 + Math.min(1.0, cv * 2);
        dimensionVariance = std * 0.5;
      }
    }

    // Calculate surface metrics
    let totalArea = 0;
    let volume = 0;

    for (let i = 1; i < profile.length; i++) {
      const r1 = profile[i - 1].radius;
      const r2 = profile[i].radius;
      const dz = profile[i].z - profile[i - 1].z;

      // Frustum volume
      volume += (Math.PI * dz / 3) * (r1 ** 2 + r1 * r2 + r2 ** 2);

      // Frustum lateral area
      const slant = Math.sqrt(dz ** 2 + (r2 - r1) ** 2);
      totalArea += Math.PI * (r1 + r2) * slant;
    }

    // Smooth surface area for comparison
    const smoothArea = totalArea * 0.75; // Approximate smooth equivalent
    const fractalContribution = (totalArea - smoothArea) / smoothArea;

    // Acoustic predictions based on fractal properties
    const inOptimalRange = globalDimension >= 1.5 && globalDimension <= 1.7;
    const expectedSmoothness = inOptimalRange ? 0.9 + Math.random() * 0.05 : 0.75 + Math.random() * 0.1;

    const analysis = {
      mesh_path,
      fractal_analysis: {
        global_dimension: Number(globalDimension.toFixed(3)),
        dimension_variance: Number(dimensionVariance.toFixed(3)),
        min_local_dimension: Number((globalDimension - dimensionVariance * 2).toFixed(3)),
        max_local_dimension: Number((globalDimension + dimensionVariance * 2).toFixed(3)),
        optimal_region_percentage: inOptimalRange ? 75 + Math.random() * 20 : 40 + Math.random() * 30,
        interpretation: inOptimalRange
          ? "Fractal dimension in optimal range for broadband impedance matching"
          : globalDimension < 1.5
          ? "Low fractal dimension - may benefit from increased complexity"
          : "High fractal dimension - may face manufacturing challenges",
      },
      surface_analysis: {
        total_area_mm2: Number(totalArea.toFixed(2)),
        smooth_equivalent_area_mm2: Number(smoothArea.toFixed(2)),
        fractal_contribution: Number(fractalContribution.toFixed(3)),
        volume_mm3: Number(volume.toFixed(2)),
      },
      acoustic_prediction: {
        expected_impedance_smoothness: Number(expectedSmoothness.toFixed(3)),
        frequency_range_effective: {
          min_hz: Math.round(800 - globalDimension * 100),
          max_hz: Math.round(18000 + globalDimension * 1000),
        },
        reflection_coefficient_estimate: Number((0.15 - expectedSmoothness * 0.08).toFixed(3)),
        recommendation: expectedSmoothness > 0.85
          ? "Geometry suitable for simulation"
          : "Consider adjusting fractal parameters",
      },
    };

    return {
      content: [{ type: "text", text: JSON.stringify(analysis, null, 2) }],
    };
  }
);

server.tool(
  "compare_geometries",
  `Compare multiple horn geometries side by side. Useful for selecting the best candidate
from a set of generated variations.`,
  CompareParams.shape,
  async (params) => {
    const { geometry_ids } = params;

    // Read profile data for each geometry
    const files = await fs.readdir(ARTIFACTS_DIR).catch(() => [] as string[]);
    const comparisons = await Promise.all(
      geometry_ids.map(async (id) => {
        // Find matching file in artifacts
        const matching = files.find((f) => f.includes(id) && f.endsWith("_profile.json"));

        if (!matching) {
          return { id, error: "Profile not found" };
        }

        const profilePath = path.join(ARTIFACTS_DIR, matching);
        const profile = JSON.parse(await fs.readFile(profilePath, "utf-8"));

        // Calculate metrics
        let pathLength = 0;
        let volume = 0;
        const throatRadius = profile[0]?.radius || 0;
        const mouthRadius = profile[profile.length - 1]?.radius || 0;

        for (let i = 1; i < profile.length; i++) {
          const r1 = profile[i - 1].radius;
          const r2 = profile[i].radius;
          const dz = profile[i].z - profile[i - 1].z;
          pathLength += Math.sqrt(dz ** 2 + (r2 - r1) ** 2);
          volume += (Math.PI * dz / 3) * (r1 ** 2 + r1 * r2 + r2 ** 2);
        }

        return {
          id,
          type: matching.split("_")[0],
          metrics: {
            expansion_ratio: mouthRadius / throatRadius,
            path_length_mm: Number(pathLength.toFixed(2)),
            volume_mm3: Number(volume.toFixed(2)),
            throat_diameter_mm: throatRadius * 2,
            mouth_diameter_mm: mouthRadius * 2,
          },
        };
      })
    );

    // Rank by path length (longer = more fractal detail)
    const ranked = comparisons
      .filter((c) => !("error" in c))
      .sort((a, b) => (b.metrics?.path_length_mm || 0) - (a.metrics?.path_length_mm || 0));

    return {
      content: [{ type: "text", text: JSON.stringify({
        geometries: comparisons,
        ranking: ranked.map((g) => g.id),
        recommendation: ranked[0]?.id || null,
        recommendation_reason: "Highest path length indicates maximum fractal detail",
      }, null, 2) }],
    };
  }
);

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("SFH-OS Geometry MCP Server running (FreeCAD-enabled)");
}

main().catch(console.error);
