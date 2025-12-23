# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install dependencies
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run a horn design project
sfh run --freq-min 1000 --freq-max 20000 --sensitivity 105

# Show system info
sfh info

# Check project status
sfh status <project-id>

# Run tests
pytest

# Lint code
ruff check sfh_os/
```

**Environment Variables:**
- `ANTHROPIC_API_KEY` - Required for Claude API access
- `SFH_MODEL` - Override default model (default: claude-sonnet-4-20250514)
- `SFH_DB_PATH` - Custom database path
- `SFH_ARTIFACTS_PATH` - Custom artifacts directory

## Project Overview

SFH-OS (Syn-Fractal Horn Orchestration System) is a multi-agent framework that autonomously bridges fractal mathematics, acoustic physics, and additive metalforming to design and manufacture 3D-printed metal acoustic horns.

## Architecture

### Orchestration Layer ("The Conductor")
- Central agent managing project lifecycle from acoustic parameters to final 3D-printed horn
- Maintains "Global State" and resolves conflicts between acoustic ideals and manufacturing constraints
- Uses MCP (Model Context Protocol) for tool execution and JSON-RPC for sub-agent messaging

### Sub-Agents
| Agent | Designation | Domain |
|-------|-------------|--------|
| Fractal Architect | AG-GEN | Recursive topology, space-filling curves (Hilbert/Peano), Mandelbrot expansion |
| Acoustic Physicist | AG-SIM | BEM simulation, impedance matching, polar response analysis |
| Fabrication Engineer | AG-MFG | Digital Sheet Forming logic, G-code optimization, Figur G15-style toolpathing |
| Quality/Verification | AG-QA | Visual inspection, acoustic sweep analysis |

### Communication Protocol
Sub-agents communicate via Manifest Files (not chat):
- **Request Manifest**: Specific goal (e.g., "Optimize Throat for 1kHz-20kHz")
- **Constraint Manifest**: Boundaries (e.g., "Max build volume: 300mm³")
- **Result Manifest**: Output (.STL files, .BEM simulation results)

The Orchestrator maintains a shared vector database containing iteration history.

## Design Pipeline Phases
1. **Generative Synthesis** (AG-GEN): Create fractal variations from target specs
2. **Acoustic Validation** (AG-SIM): Run geometries through ATH/AKABAK, return Acoustic Score based on impedance curve smoothness
3. **Figur-G15 Pathing** (AG-MFG): Optimize horn "skin" for support-free DSF printing
4. **Physical Execution**: Send instructions to 3D printer
5. **Verification** (AG-QA): Sine-sweep test comparing physical results to simulation

## External Tool Integrations (via MCP)
- **AG-GEN**: Python (NumPy/SciPy), Rhino/Grasshopper API
- **AG-SIM**: AKABAK 3, ATH, Hornresp
- **AG-MFG**: Custom slicers, Python G-code generators
- **AG-QA**: OpenCV, REW (Room EQ Wizard)

## Key Technical Concepts
- Fractal expansion minimizes reflection coefficient Γ at throat by "trapping" back-pressure (analogous to fractal antenna EM return loss management)
- Each sub-agent has specific tool permissions (e.g., only AG-SIM can write to AKABAK script folder)

## Code Structure

```
sfh_os/
├── main.py              # CLI entry point
├── config.py            # Configuration management
├── conductor/           # Orchestration layer
│   ├── orchestrator.py  # The Conductor - main loop
│   └── state.py         # Global state management
├── agents/              # Sub-agent implementations
│   ├── base.py          # Abstract BaseAgent with Claude integration
│   ├── ag_gen.py        # Fractal Architect
│   ├── ag_sim.py        # Acoustic Physicist
│   ├── ag_mfg.py        # Fabrication Engineer
│   └── ag_qa.py         # Quality/Verification
├── manifests/           # Communication protocol
│   ├── request.py       # RequestManifest (goals)
│   ├── constraint.py    # ConstraintManifest (boundaries)
│   └── result.py        # ResultManifest (outputs)
├── mcp/                 # Model Context Protocol
│   ├── protocol.py      # Tool registration/execution
│   └── tools/           # Domain-specific tools (stubs)
├── pipeline/            # Pipeline phase implementations
│   └── phase[1-5]_*.py  # Individual phase logic
└── storage/             # Persistence layer
    └── history.py       # SQLite iteration history
```

## Adding New Tools

1. Create tool functions in `sfh_os/mcp/tools/<domain>.py`
2. Define `Tool` objects with parameters and handlers
3. Set `allowed_agents` to restrict access
4. Register tools in the agent's `_register_tools()` method
