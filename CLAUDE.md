# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SFH-OS is a **Claude Code-native** autonomous framework for designing fractal acoustic horns. It uses Skills (not Python classes) as agents and MCP servers (not stub functions) as tools.

## Architecture Principles

1. **Skills ARE the agents** — Each sub-agent is a `.claude/skills/*/SKILL.md` file
2. **MCP servers ARE the tools** — Real TypeScript servers in `mcp-servers/`
3. **Claude Code IS the runtime** — No custom Python orchestrator needed
4. **JSON schemas for validation** — `schemas/*.schema.json` for manifests

## Skills (Agents)

| Skill | Purpose | Key Tools |
|-------|---------|-----------|
| `sfh-conductor` | Orchestrate pipeline, manage state, resolve conflicts | All skills |
| `sfh-gen` | Generate fractal geometries (Hilbert, Peano, Mandelbrot) | `mcp__geometry__*` |
| `sfh-sim` | Run acoustic simulations, score geometries | `mcp__acoustics__*` |
| `sfh-mfg` | Prepare for metal AM (L-PBF orientation, supports, build files) | `mcp__fabrication__*` |
| `sfh-qa` | Verify manufactured horns against predictions | `mcp__measurement__*` |
| `sfh-viz` | Generate visualizations at every phase | `mcp__visualization__*` |

## Key Files

- `.claude/skills/*/SKILL.md` — Agent definitions with domain expertise
- `.claude/settings.json` — MCP server configuration
- `schemas/*.schema.json` — Manifest validation schemas
- `mcp-servers/*/src/index.ts` — MCP tool implementations

## Working with This Project

**To invoke the full pipeline:**
```
Design a fractal horn for [frequency range] with [coverage] degrees horizontal coverage
```

**To invoke individual skills:**
```
/sfh-gen Generate 3 Mandelbrot variations
/sfh-sim Analyze this geometry's acoustic performance
/sfh-viz Create a comparison dashboard
```

## Development

**Building MCP servers:**
```bash
cd mcp-servers/<server> && npm install && npm run build
```

**Adding new tools:**
1. Add tool definition in `mcp-servers/<server>/src/index.ts`
2. Register in server's tool list
3. Add to appropriate skill's `allowed-tools` in SKILL.md

**Adding new skills:**
1. Create `.claude/skills/<skill-name>/SKILL.md`
2. Include YAML frontmatter with `name`, `description`, `allowed-tools`
3. Write domain expertise as natural language instructions

## Manifest Schemas

All agent communication uses JSON validated against:
- `schemas/request.schema.json` — Goals and specifications
- `schemas/constraint.schema.json` — Boundaries and limits
- `schemas/result.schema.json` — Outputs with scores and artifacts

## State Management

State is stored in `artifacts/state.json` (not SQLite). The Conductor reads/writes this file directly. Format:

```json
{
  "project_id": "uuid",
  "phase": "synthesis|validation|fabrication|execution|verification",
  "iteration": 1,
  "best_score": 0.92,
  "history": [...]
}
```
