# SFH-OS: Syn-Fractal Horn Orchestration System

> Autonomous Agentic Design & Manufacturing Framework for 3D-Printed Metal Acoustic Horns

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [The Innovation: Fractal Acoustics](#the-innovation-fractal-acoustics)
  - [Why Fractals?](#why-fractals)
  - [Space-Filling Curves for Sound](#space-filling-curves-for-sound)
  - [Mandelbrot Expansion Profiles](#mandelbrot-expansion-profiles)
  - [The Reflection Coefficient Problem](#the-reflection-coefficient-problem)
- [Agentic Architecture](#agentic-architecture)
  - [The Conductor: Orchestration Layer](#the-conductor-orchestration-layer)
  - [Sub-Agent Specialization](#sub-agent-specialization)
  - [Manifest-Based Communication](#manifest-based-communication)
  - [Model Context Protocol (MCP)](#model-context-protocol-mcp)
- [The 5-Phase Pipeline](#the-5-phase-pipeline)
- [Installation](#installation)
- [Usage](#usage)
- [Roadmap](#roadmap)
- [License](#license)

---

## Executive Summary

SFH-OS is an autonomous multi-agent system that bridges three domains—**fractal mathematics**, **acoustic physics**, and **additive metalforming**—to design and manufacture high-performance acoustic horns without human intervention.

Traditional horn design relies on classical expansion profiles (exponential, tractrix, conical) developed in the early 20th century. These profiles make mathematical tradeoffs that limit acoustic performance. SFH-OS breaks from tradition by applying **fractal geometry** to create expansion profiles that minimize acoustic reflections through recursive self-similarity—the same principle that makes fractal antennas efficient across wide frequency bands.

The system employs a **hierarchical agentic architecture** where a central Conductor orchestrates four specialized AI agents:

| Agent | Role | Domain Expertise |
|-------|------|------------------|
| AG-GEN | Fractal Architect | Recursive topology, space-filling curves |
| AG-SIM | Acoustic Physicist | BEM simulation, impedance analysis |
| AG-MFG | Fabrication Engineer | Toolpath generation, G-code optimization |
| AG-QA | Quality Verification | Post-print acoustic measurement |

These agents communicate not through conversation, but through structured **Manifest Files**—formal specifications of goals, constraints, and results. This architecture enables autonomous iteration: the system generates geometry variations, simulates their acoustic performance, prepares manufacturing instructions, and verifies the final product against predictions.

The deliverable is a **Production Package** containing the physical 3D-printed metal horn, a digital twin for simulation, assembly instructions, and a verification report comparing predicted vs. measured performance.

---

## The Innovation: Fractal Acoustics

### Why Fractals?

Acoustic horns face a fundamental challenge: **impedance matching**. The horn must smoothly transition acoustic impedance from a small, high-pressure driver throat to a large, low-pressure mouth radiating into open air. Any abrupt change creates reflections—sound bouncing back toward the driver, causing distortion, coloration, and efficiency loss.

Classical horn profiles (exponential, hyperbolic, tractrix) are mathematical compromises. They optimize for one aspect while sacrificing others:

- **Exponential**: Good loading, poor directivity control
- **Tractrix**: Smooth mouth termination, limited bandwidth
- **Conical**: Simple, but poor low-frequency loading

Fractals offer a fundamentally different approach: **self-similar geometry at multiple scales**.

### Space-Filling Curves for Sound

Space-filling curves like Hilbert and Peano curves have a remarkable property: they can fill a 2D or 3D space while maintaining a continuous path. When applied to horn topology:

```
Traditional Horn:           Fractal Horn:
    ___________                 _/\_/\_
   /           \               /       \
  /             \             /  /\_/\  \
 |               |           |  |     |  |
 |               |           |  |/\_/\|  |
  \             /             \  \_/\_/  /
   \___________/               \_______/
```

The fractal path creates:
- **Extended acoustic path length** within compact dimensions
- **Multiple expansion stages** that smooth impedance transitions
- **Distributed damping** of resonant modes
- **Controlled diffraction** at the mouth

### Mandelbrot Expansion Profiles

The Mandelbrot set, when mapped to horn expansion, produces profiles with **infinite detail at the boundary**. This translates to:

1. **Micro-flares**: Tiny expansions that trap high-frequency back-pressure
2. **Graduated transitions**: No single point of abrupt impedance change
3. **Frequency-dependent behavior**: Different scales interact with different wavelengths

The expansion ratio from throat to mouth follows:

```
r(z) = r_throat × (1 + (expansion_ratio - 1) × f(z))
```

Where `f(z)` is derived from Mandelbrot boundary behavior, creating a profile that appears smooth at macro scale but reveals progressive detail at micro scale.

### The Reflection Coefficient Problem

The reflection coefficient Γ at any point in the horn is:

```
Γ = (Z₂ - Z₁) / (Z₂ + Z₁)
```

Where Z₁ and Z₂ are acoustic impedances before and after that point. Traditional horns minimize Γ by making expansion gradual. Fractal horns take a different approach: **distribute reflections across infinite scales** so that:

1. Each individual reflection is microscopic
2. Reflections at different scales are phase-incoherent
3. Net reflected energy approaches zero through destructive interference

This is analogous to how fractal antennas achieve wideband performance: the self-similar structure creates multiple resonant paths that combine to produce smooth broadband behavior.

---

## Agentic Architecture

SFH-OS implements a **hierarchical multi-agent system** using the latest patterns in agentic AI architecture.

### The Conductor: Orchestration Layer

The Conductor is the central intelligence—a high-reasoning LLM that manages:

- **Global State**: Tracks project progress, iteration history, and best results
- **Conflict Resolution**: Mediates between acoustic ideals and manufacturing constraints
- **Iteration Control**: Decides when to continue optimizing vs. accept results
- **Phase Routing**: Directs work to appropriate sub-agents

```python
class Conductor:
    """Chief System Architect - manages the entire project lifecycle."""

    async def run_project(self, target_specs, constraints):
        while self.state.should_continue_iterating():
            # Phase 1: Generate geometry variations
            geometries = await self.ag_gen.generate_variations(...)

            # Phase 2: Simulate and select best
            result, best = await self.ag_sim.evaluate_variations(...)

            # Phase 3-5: Manufacturing and verification
            ...

            if self._check_convergence(result):
                break

        return await self._generate_production_package()
```

### Sub-Agent Specialization

Each sub-agent is a specialized LLM instance with:

- **Domain-specific system prompts** encoding expert knowledge
- **Restricted tool access** via MCP bindings
- **Structured I/O** through typed Manifest objects

```
┌─────────────────────────────────────────────────────────────┐
│                      THE CONDUCTOR                          │
│              (Global State + Conflict Resolution)           │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        ▼             ▼             ▼             ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
   │ AG-GEN  │  │ AG-SIM  │  │ AG-MFG  │  │ AG-QA   │
   │ Fractal │  │Acoustic │  │  Fab    │  │  QA     │
   │Architect│  │Physicist│  │Engineer │  │  Agent  │
   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
   │Geometry │  │Simulation│  │Fabrication│ │Verification│
   │  Tools  │  │  Tools  │  │  Tools  │  │  Tools  │
   └─────────┘  └─────────┘  └─────────┘  └─────────┘
```

### Manifest-Based Communication

Agents don't "chat"—they exchange formal **Manifests**:

**Request Manifest**: What to accomplish
```json
{
  "request_type": "generate_geometry",
  "goal": "Design fractal horn for 1kHz-20kHz",
  "specs": {
    "frequency_range": {"min_hz": 1000, "max_hz": 20000},
    "target_sensitivity_db": 105,
    "coverage_angle_h": 90
  }
}
```

**Constraint Manifest**: Boundaries to respect
```json
{
  "dimensional": {"max_width_mm": 300, "max_depth_mm": 400},
  "manufacturing": {"support_allowed": false, "max_overhang_angle_deg": 45},
  "acoustic": {"min_sensitivity_db": 100, "max_deviation_db": 3}
}
```

**Result Manifest**: What was produced
```json
{
  "status": "success",
  "acoustic_score": {"impedance_smoothness": 0.92, "overall": 0.89},
  "artifacts": [{"type": "stl", "path": "horn_v3.stl"}]
}
```

This structured communication enables:
- **Reproducibility**: Every decision is logged
- **Debugging**: Trace exactly why an agent made a choice
- **Iteration**: Modify constraints and re-run without ambiguity

### Model Context Protocol (MCP)

MCP provides **tool binding with permission control**:

```python
Tool(
    name="run_bem_simulation",
    description="Run Boundary Element Method acoustic simulation",
    parameters=[...],
    handler=run_bem_simulation,
    allowed_agents=["AG-SIM"],  # Only acoustic physicist can use this
)
```

This enforces separation of concerns:
- AG-GEN cannot run simulations (only generate geometry)
- AG-MFG cannot modify acoustic parameters (only manufacturing)
- AG-QA has read-only access to compare results

---

## The 5-Phase Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 1: GENERATIVE SYNTHESIS                                    │
│ AG-GEN creates 3 fractal variations using different approaches:  │
│ • Hilbert curve topology                                         │
│ • Peano space-filling                                            │
│ • Mandelbrot expansion                                           │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 2: ACOUSTIC VALIDATION                                     │
│ AG-SIM runs BEM simulation on each variation:                    │
│ • Impedance curve analysis                                       │
│ • Polar response calculation                                     │
│ • Frequency response measurement                                 │
│ → Selects best variation by Acoustic Score                       │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 3: FIGUR-G15 PATHING                                       │
│ AG-MFG prepares for Digital Sheet Forming:                       │
│ • Printability analysis (overhangs, thin walls)                  │
│ • Skin thickness optimization                                    │
│ • DSF toolpath generation                                        │
│ • G-code production and validation                               │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 4: PHYSICAL EXECUTION                                      │
│ Conductor sends instructions to 3D printer:                      │
│ • G-code upload                                                  │
│ • Print monitoring                                               │
│ • Error handling                                                 │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ PHASE 5: VERIFICATION                                            │
│ AG-QA performs post-print validation:                            │
│ • Visual inspection (OpenCV)                                     │
│ • Acoustic sine sweep (REW)                                      │
│ • Compare measured vs. simulated                                 │
│ → Pass: Generate Production Package                              │
│ → Fail: Return to Phase 1 with learned constraints               │
└──────────────────────────────────────────────────────────────────┘
```

The pipeline is **iterative**: if verification fails, the system automatically adjusts parameters and tries again, up to a configurable maximum iterations.

---

## Installation

```bash
git clone https://github.com/toneron2/SFH-OS.git
cd SFH-OS
pip install -e ".[dev]"
```

**Requirements:**
- Python 3.11+
- Anthropic API key

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

---

## Usage

**Run a horn design project:**
```bash
sfh run --freq-min 1000 --freq-max 20000 --sensitivity 105 --coverage-h 90
```

**Check system configuration:**
```bash
sfh info
```

**Monitor project status:**
```bash
sfh status <project-id>
```

---

## Roadmap

- [ ] **Real tool integrations**: Connect AKABAK, Hornresp, OpenCV, REW
- [ ] **Hardware interface**: Direct printer control via OctoPrint/Klipper
- [ ] **Web UI**: Visual monitoring dashboard
- [ ] **Parametric optimization**: Genetic algorithms for fractal parameters
- [ ] **Multi-material support**: Composite horn construction

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <i>Bridging fractal mathematics, acoustic physics, and autonomous manufacturing</i>
</p>
