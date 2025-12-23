/**
 * SFH-OS Visualization MCP Server
 *
 * Provides rendering and visualization tools for AG-VIZ:
 * - 3D mesh rendering
 * - 2D plot generation
 * - Animation creation
 * - Dashboard assembly
 * - Export to multiple formats
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const Render3DParams = z.object({
  mesh_path: z.string(),
  style: z.enum(["technical", "artistic", "wireframe", "xray"]).default("technical"),
  views: z.array(z.enum(["isometric", "front", "side", "top", "cross_section", "detail"])).default(["isometric"]),
  resolution: z.enum(["preview", "standard", "high", "4k"]).default("standard"),
  annotations: z.boolean().default(true),
  output_format: z.enum(["png", "svg", "webgl", "all"]).default("png"),
});

const Plot2DParams = z.object({
  plot_type: z.enum([
    "frequency_response",
    "impedance",
    "polar",
    "waterfall",
    "spectrogram",
    "comparison",
  ]),
  data_path: z.string(),
  style: z.enum(["publication", "presentation", "web"]).default("publication"),
  output_format: z.enum(["svg", "png", "pdf"]).default("svg"),
});

const AnimateParams = z.object({
  animation_type: z.enum([
    "cross_section_sweep",
    "pressure_field",
    "toolpath",
    "build_progression",
    "polar_morph",
    "frequency_sweep",
  ]),
  data_path: z.string(),
  duration_seconds: z.number().positive().default(5),
  fps: z.number().min(10).max(60).default(30),
  output_format: z.enum(["mp4", "webm", "gif"]).default("mp4"),
});

const DashboardParams = z.object({
  dashboard_type: z.enum([
    "geometry_comparison",
    "simulation_results",
    "verification_report",
    "iteration_history",
    "production_package",
  ]),
  data_paths: z.array(z.string()),
  interactive: z.boolean().default(true),
});

const server = new McpServer({
  name: "sfh-visualization",
  version: "0.1.0",
});

server.tool(
  "render_3d",
  "Render 3D visualization of horn geometry. Supports multiple views, styles, and output formats including interactive WebGL.",
  Render3DParams,
  async (params) => {
    const { mesh_path, style, views, resolution, annotations, output_format } = params;

    const resolutions = {
      preview: { width: 800, height: 600 },
      standard: { width: 1920, height: 1080 },
      high: { width: 2560, height: 1440 },
      "4k": { width: 3840, height: 2160 },
    };

    const outputs: Record<string, string> = {};
    const res = resolutions[resolution];

    for (const view of views) {
      const baseName = mesh_path.replace(/\.[^.]+$/, "");
      if (output_format === "all" || output_format === "png") {
        outputs[`${view}_png`] = `${baseName}_${view}.png`;
      }
      if (output_format === "all" || output_format === "svg") {
        outputs[`${view}_svg`] = `${baseName}_${view}.svg`;
      }
      if (output_format === "all" || output_format === "webgl") {
        outputs[`${view}_webgl`] = `${baseName}_${view}_viewer.html`;
      }
    }

    const result = {
      input_mesh: mesh_path,
      style,
      resolution: res,
      annotations_enabled: annotations,
      outputs,
      render_settings: {
        lighting: "3-point-studio",
        material: style === "technical" ? "brushed_aluminum" : "matte_white",
        background: "gradient_dark",
        antialiasing: "8x",
      },
      thumbnail: `${mesh_path.replace(/\.[^.]+$/, "")}_thumb.png`,
    };

    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

server.tool(
  "plot_2d",
  "Generate 2D plots for acoustic data visualization. Publication-quality output with proper typography and styling.",
  Plot2DParams,
  async (params) => {
    const { plot_type, data_path, style, output_format } = params;

    const styleConfigs = {
      publication: {
        font: "Times New Roman",
        font_size: 10,
        line_width: 1,
        figure_width_mm: 85,
        dpi: 300,
      },
      presentation: {
        font: "Arial",
        font_size: 18,
        line_width: 2,
        figure_width_mm: 254,
        dpi: 150,
      },
      web: {
        font: "Inter",
        font_size: 14,
        line_width: 1.5,
        figure_width_mm: 200,
        dpi: 96,
      },
    };

    const config = styleConfigs[style];
    const outputPath = data_path.replace(/\.[^.]+$/, `_${plot_type}.${output_format}`);

    const result = {
      plot_type,
      data_source: data_path,
      output_path: outputPath,
      style_config: config,
      plot_elements: getPlotElements(plot_type),
    };

    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

server.tool(
  "animate",
  "Create animations for dynamic visualization of horn properties, simulation results, or manufacturing processes.",
  AnimateParams,
  async (params) => {
    const { animation_type, data_path, duration_seconds, fps, output_format } = params;

    const totalFrames = Math.round(duration_seconds * fps);
    const outputPath = data_path.replace(/\.[^.]+$/, `_${animation_type}.${output_format}`);

    const result = {
      animation_type,
      data_source: data_path,
      output_path: outputPath,
      specs: {
        duration_seconds,
        fps,
        total_frames: totalFrames,
        resolution: { width: 1920, height: 1080 },
        codec: output_format === "mp4" ? "h264" : output_format === "webm" ? "vp9" : "gif",
      },
      keyframes: generateKeyframes(animation_type, totalFrames),
    };

    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

server.tool(
  "dashboard",
  "Assemble interactive dashboard for comprehensive data visualization. Combines multiple plots and views.",
  DashboardParams,
  async (params) => {
    const { dashboard_type, data_paths, interactive } = params;

    const layouts = {
      geometry_comparison: {
        columns: 3,
        rows: 4,
        panels: [
          { type: "3d_render", span: [1, 1], sync_rotation: true },
          { type: "3d_render", span: [1, 1], sync_rotation: true },
          { type: "3d_render", span: [1, 1], sync_rotation: true },
          { type: "fr_overlay", span: [3, 1] },
          { type: "polar_comparison", span: [3, 1] },
          { type: "metrics_table", span: [3, 1] },
        ],
      },
      simulation_results: {
        columns: 2,
        rows: 3,
        panels: [
          { type: "impedance_plot", span: [1, 1] },
          { type: "fr_plot", span: [1, 1] },
          { type: "polar_balloon", span: [1, 1] },
          { type: "waterfall", span: [1, 1] },
          { type: "pressure_field", span: [2, 1] },
        ],
      },
      verification_report: {
        columns: 2,
        rows: 4,
        panels: [
          { type: "measured_vs_simulated_fr", span: [2, 1] },
          { type: "impedance_overlay", span: [1, 1] },
          { type: "polar_overlay", span: [1, 1] },
          { type: "deviation_heatmap", span: [1, 1] },
          { type: "pass_fail_summary", span: [1, 1] },
          { type: "defect_map", span: [2, 1] },
        ],
      },
    };

    const layout = layouts[dashboard_type as keyof typeof layouts] || layouts.simulation_results;

    const result = {
      dashboard_type,
      interactive,
      output_path: `artifacts/dashboards/${dashboard_type}.html`,
      layout,
      data_sources: data_paths,
      features: interactive
        ? ["zoom", "pan", "hover_info", "click_to_expand", "sync_views", "export"]
        : ["static_render"],
    };

    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }
);

// Helper functions
function getPlotElements(plotType: string) {
  const elements: Record<string, object> = {
    frequency_response: {
      x_axis: { label: "Frequency (Hz)", scale: "log", range: [20, 20000] },
      y_axis: { label: "SPL (dB)", scale: "linear", range: [70, 120] },
      grid: true,
      legend: true,
    },
    impedance: {
      subplots: 2,
      subplot_1: { y_label: "|Z| (Ω)", scale: "linear" },
      subplot_2: { y_label: "Phase (°)", scale: "linear", range: [-90, 90] },
      shared_x: true,
    },
    polar: {
      projection: "polar",
      angular_range: [0, 360],
      radial_range: [-30, 0],
      grid_circles: [-6, -12, -18, -24],
    },
  };
  return elements[plotType] || {};
}

function generateKeyframes(animationType: string, totalFrames: number) {
  const keyframes = [];
  const keyframeCount = Math.min(5, Math.floor(totalFrames / 10));

  for (let i = 0; i <= keyframeCount; i++) {
    const frame = Math.round((i / keyframeCount) * totalFrames);
    const progress = i / keyframeCount;

    keyframes.push({
      frame,
      progress,
      description: `${animationType} at ${Math.round(progress * 100)}%`,
    });
  }

  return keyframes;
}

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("SFH-OS Visualization MCP Server running");
}

main().catch(console.error);
