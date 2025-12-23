# Phase Transition Hook

This hook is invoked when the SFH-OS pipeline transitions between phases.

## Trigger

Invoked automatically when:
- A phase completes successfully
- The Conductor decides to advance the pipeline
- An iteration loop restarts

## Actions

1. **State Persistence**: Save current state to `artifacts/state.json`
2. **Visualization**: Generate summary visualization of completed phase
3. **Logging**: Append to iteration history
4. **Notification**: Alert user of phase transition (if configured)

## Usage

```bash
# Called by Conductor after each phase
.claude/hooks/phase-transition.sh <from_phase> <to_phase> <iteration>
```

## Example

```bash
.claude/hooks/phase-transition.sh synthesis validation 3
```

This would:
1. Save AG-GEN results to state
2. Generate geometry summary visualization
3. Log: "Iteration 3: synthesis → validation"
4. Prepare AG-SIM invocation context
