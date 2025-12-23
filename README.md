# SFH-OS: Syn-Fractal Horn Orchestration System

> A Claude Code-native autonomous framework for designing and manufacturing fractal acoustic horns

[![Claude Code](https://img.shields.io/badge/Claude%20Code-Native-blueviolet)](https://claude.ai/code)
[![MCP](https://img.shields.io/badge/MCP-1.0-green)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [The Innovation: Fractal Acoustics](#the-innovation-fractal-acoustics)
- [Claude Code-Native Architecture](#claude-code-native-architecture)
- [The 5-Phase Pipeline](#the-5-phase-pipeline)
- [Deep Visualization](#deep-visualization)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)

---

## Executive Summary

SFH-OS represents a new paradigm in autonomous design systems: **the process is as innovative as the product**.

### The Product: Fractal Acoustic Horns

Traditional horn loudspeakers use expansion profiles (exponential, tractrix) from the 1920s. These are mathematical compromises. SFH-OS applies **fractal geometry** to create horns with:

- **Distributed impedance matching** via self-similar expansion
- **Wideband performance** through multi-scale resonance (like fractal antennas)
- **Minimized reflections** by phase-canceling micro-reflections across scales

The result: acoustic performance impossible with classical geometry.

### The Process: Claude Code-Native Agentic System

SFH-OS doesn't wrap Claude in Python—**it makes Claude Code the runtime**:

| Traditional Approach | SFH-OS Approach |
|---------------------|-----------------|
| Python agent classes | Claude Code Skills (SKILL.md) |
| Custom orchestrator | Conductor skill orchestrates natively |
| Stub tool functions | Real MCP servers (TypeScript) |
| Pydantic models | JSON Schemas validated by Claude |
| SQLite state | File-based state Claude reads/writes |

This is **2026-aware engineering**: declarative agent definitions, composable MCP tools, and Claude Code as the execution environment.

---

## The Innovation: Fractal Acoustics

### The Impedance Problem

A horn matches the high acoustic impedance at the driver throat to the low impedance of open air. The reflection coefficient at any point:

```
Γ = (Z₂ - Z₁) / (Z₂ + Z₁)
```

**Traditional solution**: Gradual expansion (minimize each Γ)
**Fractal solution**: Infinite tiny reflections that destructively interfere

### Space-Filling Curves

Hilbert and Peano curves fill space while maintaining continuity:

```
Hilbert Order 3:          Applied to Horn:
    _   _                      _/\_
   | |_| |                    /    \
   |_   _|    ───────►       /  /\  \
     |_|                    |  |  |  |
                            \  \/  /
                             \_  _/
```

Properties when applied to horn topology:
- **Path length**: 6-10× geometric length (more expansion distance)
- **Locality**: Adjacent curve points stay spatially close
- **Scalability**: Order controls frequency interaction scale

### Mandelbrot Expansion

The Mandelbrot set boundary has infinite perimeter in finite area. Mapped to horn expansion:

```python
z_{n+1} = z_n² + c  # Iterate to find boundary distance
r(position) = throat_r × mandelbrot_expansion(position)
```

This creates:
- Smooth large-scale expansion (main cardioid)
- Infinite small-scale detail (boundary fractal)
- Different `c` values = different horn characters

### The Fractal Dimension Sweet Spot

For acoustic horns, optimal fractal dimension D = **1.5 to 1.7**:

| D Value | Characteristic | Acoustic Effect |
|---------|---------------|-----------------|
| < 1.3 | Too smooth | Loses fractal benefits |
| 1.5-1.7 | Optimal | Broadband impedance matching |
| > 2.0 | Too complex | Unmaufacturable, viscous losses |

---

## Claude Code-Native Architecture

### Skills ARE the Agents

Each sub-agent is defined as a Claude Code Skill with SKILL.md:

```
.claude/skills/
├── sfh-conductor/     # The Conductor - orchestration intelligence
│   └── SKILL.md       # Manages pipeline, resolves conflicts
├── sfh-gen/           # AG-GEN - Fractal Architect
│   ├── SKILL.md       # Geometry generation expertise
│   └── fractal-theory.md  # Domain knowledge
├── sfh-sim/           # AG-SIM - Acoustic Physicist
│   └── SKILL.md       # BEM simulation, scoring
├── sfh-mfg/           # AG-MFG - Fabrication Engineer
│   └── SKILL.md       # DSF toolpathing, G-code
├── sfh-qa/            # AG-QA - Quality Verification
│   └── SKILL.md       # Measurement, comparison
└── sfh-viz/           # AG-VIZ - Visual Architect
    └── SKILL.md       # Rendering, dashboards
```

Skills include:
- YAML frontmatter with `allowed-tools` for permission control
- Rich domain expertise encoded as natural language
- Reference documents Claude can consult
- Invocation patterns for tool use

### MCP Servers ARE the Tools

Real TypeScript MCP servers provide capabilities:

```
mcp-servers/
├── geometry/          # Fractal generation (Hilbert, Peano, Mandelbrot)
├── acoustics/         # BEM simulation, impedance analysis
├── fabrication/       # Toolpath generation, G-code
├── measurement/       # Post-print verification
└── visualization/     # Rendering, plotting, animation
```

Each server:
- Implements Model Context Protocol
- Exposes tools Claude can invoke
- Is swappable (mock → real implementation)
- Is language-agnostic (could be Python, Rust, etc.)

### JSON Schemas for Manifests

Communication via validated JSON:

```
schemas/
├── request.schema.json    # Goals for sub-agents
├── constraint.schema.json # Boundaries to respect
└── result.schema.json     # Outputs with scores
```

Claude validates against these schemas natively—no Pydantic required.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLAUDE CODE RUNTIME                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    sfh-conductor SKILL                       │   │
│   │        (Orchestration, State Management, Conflicts)          │   │
│   └─────────────────────────┬───────────────────────────────────┘   │
│                             │                                       │
│         ┌───────────────────┼───────────────────┐                   │
│         ▼                   ▼                   ▼                   │
│   ┌───────────┐       ┌───────────┐       ┌───────────┐            │
│   │ sfh-gen   │       │ sfh-sim   │       │ sfh-mfg   │   ...      │
│   │  SKILL    │       │  SKILL    │       │  SKILL    │            │
│   └─────┬─────┘       └─────┬─────┘       └─────┬─────┘            │
│         │                   │                   │                   │
├─────────┼───────────────────┼───────────────────┼───────────────────┤
│         ▼                   ▼                   ▼                   │
│   ┌───────────┐       ┌───────────┐       ┌───────────┐            │
│   │ geometry  │       │ acoustics │       │fabrication│            │
│   │MCP Server │       │MCP Server │       │MCP Server │   ...      │
│   └───────────┘       └───────────┘       └───────────┘            │
│                                                                     │
│                      MCP TOOL LAYER                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## The 5-Phase Pipeline

```
     User: "Design a horn for 1kHz-20kHz, 90° coverage"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1: GENERATIVE SYNTHESIS (sfh-gen)                            │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   Hilbert   │  │    Peano    │  │  Mandelbrot │                 │
│  │   Order 4   │  │  Iteration 3│  │  c=-0.75+0i │                 │
│  │   D=1.52    │  │    D=1.71   │  │    D=1.63   │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
│                                                                     │
│  Visualize: 3D renders, fractal dimension maps, cross-sections      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 2: ACOUSTIC VALIDATION (sfh-sim)                             │
│                                                                     │
│  For each variation:                                                │
│  • Run BEM simulation (500Hz - 20kHz)                              │
│  • Analyze impedance curve (smoothness S)                          │
│  • Calculate polar response                                        │
│  • Compute Acoustic Score                                          │
│                                                                     │
│  Select winner: Highest overall score                              │
│                                                                     │
│  Visualize: Impedance plots, waterfall, polar balloons, pressure   │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 3: FABRICATION PREPARATION (sfh-mfg)                         │
│                                                                     │
│  • Printability analysis (overhangs, thin walls)                   │
│  • Thickness optimization (acoustic + structural)                  │
│  • DSF toolpath generation (spiral + layer hybrid)                 │
│  • G-code production and validation                                │
│                                                                     │
│  Constraint: NO SUPPORTS (DSF requirement)                         │
│                                                                     │
│  Visualize: Printability heatmap, toolpath animation, build sim    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 4: PHYSICAL EXECUTION                                        │
│                                                                     │
│  • Upload G-code to Figur G15 (or compatible DSF machine)          │
│  • Monitor print progress                                          │
│  • Handle errors, pauses, material changes                         │
│                                                                     │
│  Output: Physical aluminum horn                                    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 5: VERIFICATION (sfh-qa)                                     │
│                                                                     │
│  • Visual inspection (surface defects, dimensions)                 │
│  • Acoustic sine sweep (20Hz - 20kHz)                              │
│  • Impedance measurement                                           │
│  • Compare measured vs. simulated                                  │
│                                                                     │
│  Decision: PASS → Production Package                               │
│            FAIL → Iterate with learned constraints                 │
│                                                                     │
│  Visualize: Overlay plots, deviation heatmaps, comparison dash     │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        ┌─────────┐                    ┌─────────────┐
        │  PASS   │                    │    FAIL     │
        └────┬────┘                    └──────┬──────┘
             │                                │
             ▼                                ▼
    Production Package              Return to Phase 1
    • Physical horn                 • Updated constraints
    • Digital twin                  • Learned parameters
    • Assembly manual               • Conflict resolutions
    • Verification report
```

---

## Deep Visualization

AG-VIZ provides comprehensive visualization throughout the pipeline:

### Geometry Visualization
- **3D Renders**: Isometric, cross-section, detail views
- **Fractal Maps**: Local dimension D color-coded on surface
- **Animation**: Cross-section sweep revealing internal structure

### Acoustic Visualization
- **Impedance Plots**: Magnitude + phase vs. frequency
- **Waterfall**: SPL vs. frequency vs. angle (3D surface)
- **Polar Balloons**: 3D directivity at key frequencies
- **Pressure Fields**: Animated acoustic pressure inside horn

### Manufacturing Visualization
- **Printability Heatmap**: Overhang angles color-coded
- **Toolpath Animation**: DSF tool motion preview
- **Build Simulation**: Layer-by-layer progression

### Comparison & Reporting
- **Variation Dashboard**: Side-by-side geometry comparison
- **Measured vs. Simulated**: Overlay plots with deviation bands
- **Iteration Journey**: Score progression across optimization

All visualizations export to: PNG, SVG, PDF, MP4, GIF, WebGL (interactive)

---

## Getting Started

### Prerequisites

- **Claude Code** with MCP support
- **Node.js** 20+ (for MCP servers)
- **Anthropic API key**

### Installation

```bash
# Clone repository
git clone https://github.com/toneron2/SFH-OS.git
cd SFH-OS

# Install MCP servers
cd mcp-servers/geometry && npm install && npm run build && cd ../..
cd mcp-servers/acoustics && npm install && npm run build && cd ../..
cd mcp-servers/visualization && npm install && npm run build && cd ../..

# Configure Claude Code to use SFH-OS skills
# The .claude/ directory is auto-detected
```

### Usage

Open Claude Code in the SFH-OS directory. The skills are automatically available:

```
You: Design a fractal horn for 1kHz to 20kHz with 90° horizontal coverage

Claude: [Invokes sfh-conductor skill]
        [Conductor orchestrates sfh-gen → sfh-sim → sfh-mfg → sfh-qa]
        [Generates visualizations at each phase]
        [Produces production package]
```

Or invoke skills directly:

```
You: /sfh-gen Generate 3 Mandelbrot horn variations with c=-0.75

You: /sfh-viz Create a comparison dashboard for these geometries
```

---

## Project Structure

```
SFH-OS/
├── .claude/
│   ├── skills/
│   │   ├── sfh-conductor/SKILL.md    # Orchestration
│   │   ├── sfh-gen/                   # Fractal Architect
│   │   │   ├── SKILL.md
│   │   │   └── fractal-theory.md
│   │   ├── sfh-sim/SKILL.md          # Acoustic Physicist
│   │   ├── sfh-mfg/SKILL.md          # Fabrication Engineer
│   │   ├── sfh-qa/SKILL.md           # Quality Verification
│   │   └── sfh-viz/SKILL.md          # Visual Architect
│   ├── settings.json                  # MCP server config
│   └── hooks/                         # Pipeline automation
├── mcp-servers/
│   ├── geometry/                      # Fractal generation
│   ├── acoustics/                     # BEM simulation
│   ├── fabrication/                   # Toolpathing
│   ├── measurement/                   # Verification
│   └── visualization/                 # Rendering
├── schemas/
│   ├── request.schema.json
│   ├── constraint.schema.json
│   └── result.schema.json
├── artifacts/                         # Generated outputs
│   ├── geometry/
│   ├── simulation/
│   ├── visualization/
│   └── production/
├── CLAUDE.md                          # Claude Code guidance
└── README.md
```

---

## Roadmap

### Phase 1: Foundation (Current)
- [x] Skill definitions for all agents
- [x] MCP server interfaces
- [x] JSON schemas for manifests
- [x] Visualization skill design

### Phase 2: Tool Implementation
- [ ] Real geometry generation (Three.js + math algorithms)
- [ ] Acoustic simulation integration (AKABAK, Hornresp)
- [ ] G-code generation for Figur G15
- [ ] Measurement integration (REW, OpenCV)

### Phase 3: Hardware Integration
- [ ] Printer control via OctoPrint/Klipper
- [ ] Automated measurement rig
- [ ] Closed-loop iteration

### Phase 4: Advanced Features
- [ ] Genetic algorithm optimization for fractal parameters
- [ ] Multi-material horn construction
- [ ] Real-time acoustic monitoring during print
- [ ] Web dashboard for remote monitoring

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <b>Innovation Parity</b><br>
  <i>The process is as novel as the product</i><br><br>
  Fractal Mathematics × Acoustic Physics × Agentic AI × Metal Additive Manufacturing
</p>
