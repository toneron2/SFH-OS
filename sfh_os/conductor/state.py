"""Global State - Maintains project state across iterations."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sfh_os.manifests import ConstraintManifest, RequestManifest, ResultManifest


class ProjectPhase(str, Enum):
    """Current phase of the project."""

    INITIALIZED = "initialized"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    PATHING = "pathing"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    COMPLETE = "complete"
    FAILED = "failed"


class ConflictType(str, Enum):
    """Types of conflicts that can occur between agents."""

    CONSTRAINT_VIOLATION = "constraint_violation"
    ACOUSTIC_MANUFACTURING_TRADEOFF = "acoustic_manufacturing_tradeoff"
    ITERATION_LIMIT = "iteration_limit"
    VERIFICATION_FAILURE = "verification_failure"


@dataclass
class Conflict:
    """Represents a conflict between agent requirements."""

    id: UUID = field(default_factory=uuid4)
    conflict_type: ConflictType = ConflictType.CONSTRAINT_VIOLATION
    source_agent: str = ""
    target_agent: str = ""
    description: str = ""
    proposed_resolution: str | None = None
    resolved: bool = False
    resolution_action: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class IterationRecord:
    """Record of a single iteration through the pipeline."""

    iteration_number: int
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    phase_reached: ProjectPhase = ProjectPhase.INITIALIZED
    geometry_result: ResultManifest | None = None
    simulation_result: ResultManifest | None = None
    fabrication_result: ResultManifest | None = None
    verification_result: ResultManifest | None = None
    conflicts: list[Conflict] = field(default_factory=list)
    success: bool = False


class GlobalState:
    """Maintains the global state of an SFH-OS project.

    The Conductor uses this to track:
    - Current project phase
    - Iteration history
    - Active manifests
    - Conflicts and resolutions
    - Best results achieved
    """

    def __init__(self):
        self.project_id: UUID = uuid4()
        self.created_at: datetime = datetime.utcnow()
        self.current_phase: ProjectPhase = ProjectPhase.INITIALIZED
        self.current_iteration: int = 0
        self.max_iterations: int = 10

        # Manifest storage
        self.active_request: RequestManifest | None = None
        self.active_constraints: ConstraintManifest | None = None

        # Iteration history
        self.iterations: list[IterationRecord] = []
        self.current_iteration_record: IterationRecord | None = None

        # Best results tracking
        self.best_acoustic_score: float = 0.0
        self.best_iteration: int = 0
        self.best_geometry: ResultManifest | None = None
        self.best_simulation: ResultManifest | None = None

        # Conflict tracking
        self.active_conflicts: list[Conflict] = []
        self.resolved_conflicts: list[Conflict] = []

    def start_iteration(self) -> IterationRecord:
        """Start a new iteration."""
        self.current_iteration += 1
        record = IterationRecord(iteration_number=self.current_iteration)
        self.current_iteration_record = record
        self.iterations.append(record)
        return record

    def complete_iteration(self, success: bool = True) -> None:
        """Complete the current iteration."""
        if self.current_iteration_record:
            self.current_iteration_record.completed_at = datetime.utcnow()
            self.current_iteration_record.success = success

            # Update best results if this iteration was better
            if (
                self.current_iteration_record.simulation_result
                and self.current_iteration_record.simulation_result.acoustic_score
            ):
                score = self.current_iteration_record.simulation_result.acoustic_score.overall
                if score > self.best_acoustic_score:
                    self.best_acoustic_score = score
                    self.best_iteration = self.current_iteration
                    self.best_geometry = self.current_iteration_record.geometry_result
                    self.best_simulation = self.current_iteration_record.simulation_result

    def set_phase(self, phase: ProjectPhase) -> None:
        """Update the current phase."""
        self.current_phase = phase
        if self.current_iteration_record:
            self.current_iteration_record.phase_reached = phase

    def record_geometry_result(self, result: ResultManifest) -> None:
        """Record geometry generation result."""
        if self.current_iteration_record:
            self.current_iteration_record.geometry_result = result

    def record_simulation_result(self, result: ResultManifest) -> None:
        """Record simulation result."""
        if self.current_iteration_record:
            self.current_iteration_record.simulation_result = result

    def record_fabrication_result(self, result: ResultManifest) -> None:
        """Record fabrication result."""
        if self.current_iteration_record:
            self.current_iteration_record.fabrication_result = result

    def record_verification_result(self, result: ResultManifest) -> None:
        """Record verification result."""
        if self.current_iteration_record:
            self.current_iteration_record.verification_result = result

    def add_conflict(self, conflict: Conflict) -> None:
        """Add a conflict to be resolved."""
        self.active_conflicts.append(conflict)
        if self.current_iteration_record:
            self.current_iteration_record.conflicts.append(conflict)

    def resolve_conflict(self, conflict_id: UUID, resolution: str) -> bool:
        """Resolve a conflict."""
        for conflict in self.active_conflicts:
            if conflict.id == conflict_id:
                conflict.resolved = True
                conflict.resolution_action = resolution
                self.active_conflicts.remove(conflict)
                self.resolved_conflicts.append(conflict)
                return True
        return False

    def should_continue_iterating(self) -> bool:
        """Check if more iterations should be attempted."""
        if self.current_iteration >= self.max_iterations:
            return False
        if self.current_phase == ProjectPhase.COMPLETE:
            return False
        if self.current_phase == ProjectPhase.FAILED:
            return False
        return True

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the current state."""
        return {
            "project_id": str(self.project_id),
            "current_phase": self.current_phase.value,
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "best_acoustic_score": self.best_acoustic_score,
            "best_iteration": self.best_iteration,
            "total_conflicts": len(self.active_conflicts) + len(self.resolved_conflicts),
            "active_conflicts": len(self.active_conflicts),
            "iterations_completed": len([i for i in self.iterations if i.completed_at]),
        }

    def to_context(self) -> str:
        """Generate context string for agent prompts."""
        summary = self.get_summary()
        lines = [
            "## Project State Context",
            f"**Project ID:** {summary['project_id']}",
            f"**Phase:** {summary['current_phase']}",
            f"**Iteration:** {summary['current_iteration']}/{summary['max_iterations']}",
            f"**Best Score:** {summary['best_acoustic_score']:.2%} (iteration {summary['best_iteration']})",
        ]

        if self.active_conflicts:
            lines.append("\n### Active Conflicts")
            for conflict in self.active_conflicts:
                lines.append(f"- [{conflict.conflict_type.value}] {conflict.description}")

        return "\n".join(lines)
