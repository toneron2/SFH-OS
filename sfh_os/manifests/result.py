"""Result Manifest - Contains output from sub-agent operations."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ResultStatus(str, Enum):
    """Status of a result."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    PENDING = "pending"


class ArtifactType(str, Enum):
    """Types of artifacts that can be produced."""

    STL = "stl"
    STEP = "step"
    GCODE = "gcode"
    BEM_RESULT = "bem_result"
    SIMULATION_DATA = "simulation_data"
    IMAGE = "image"
    REPORT = "report"
    MEASUREMENT = "measurement"


class Artifact(BaseModel):
    """An artifact produced by an agent."""

    id: UUID = Field(default_factory=uuid4)
    artifact_type: ArtifactType
    path: Path | None = None
    data: dict[str, Any] | None = None
    checksum: str | None = None
    size_bytes: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AcousticScore(BaseModel):
    """Acoustic performance scoring."""

    impedance_smoothness: float = Field(ge=0, le=1, description="Z_a curve smoothness score")
    frequency_response_flatness: float = Field(ge=0, le=1)
    polar_uniformity: float = Field(ge=0, le=1)
    distortion_score: float = Field(ge=0, le=1)
    overall: float = Field(ge=0, le=1)

    @classmethod
    def from_simulation(cls, sim_data: dict[str, Any]) -> "AcousticScore":
        """Create score from simulation data."""
        return cls(
            impedance_smoothness=sim_data.get("impedance_smoothness", 0.5),
            frequency_response_flatness=sim_data.get("fr_flatness", 0.5),
            polar_uniformity=sim_data.get("polar_uniformity", 0.5),
            distortion_score=sim_data.get("distortion_score", 0.5),
            overall=sim_data.get("overall_score", 0.5),
        )


class GeometryMetrics(BaseModel):
    """Metrics for generated geometry."""

    volume_mm3: float = 0
    surface_area_mm2: float = 0
    fractal_dimension: float = Field(default=1.0, ge=1.0, le=3.0)
    expansion_ratio: float = 1.0
    path_length_mm: float = 0
    vertex_count: int = 0
    face_count: int = 0


class ResultManifest(BaseModel):
    """Result Manifest for agent communication.

    Contains the output from a sub-agent operation.
    """

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    request_id: UUID = Field(description="Associated request manifest ID")
    source_agent: str = Field(description="Agent that produced this result")
    status: ResultStatus = Field(default=ResultStatus.PENDING)
    message: str = Field(default="")
    artifacts: list[Artifact] = Field(default_factory=list)
    acoustic_score: AcousticScore | None = None
    geometry_metrics: GeometryMetrics | None = None
    raw_output: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    execution_time_seconds: float | None = None
    iteration: int = Field(default=1)

    def mark_complete(self, status: ResultStatus = ResultStatus.SUCCESS) -> None:
        """Mark this result as complete."""
        self.completed_at = datetime.utcnow()
        self.status = status
        if self.created_at:
            delta = self.completed_at - self.created_at
            self.execution_time_seconds = delta.total_seconds()

    def add_artifact(
        self,
        artifact_type: ArtifactType,
        path: Path | None = None,
        data: dict[str, Any] | None = None,
        **metadata: Any,
    ) -> Artifact:
        """Add an artifact to this result."""
        artifact = Artifact(
            artifact_type=artifact_type,
            path=path,
            data=data,
            metadata=metadata,
        )
        self.artifacts.append(artifact)
        return artifact

    def to_summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            f"## Result Summary",
            f"**Status:** {self.status.value}",
            f"**Source:** {self.source_agent}",
            f"**Message:** {self.message}",
        ]

        if self.acoustic_score:
            lines.extend([
                "",
                "### Acoustic Score",
                f"- Impedance Smoothness: {self.acoustic_score.impedance_smoothness:.2%}",
                f"- FR Flatness: {self.acoustic_score.frequency_response_flatness:.2%}",
                f"- Polar Uniformity: {self.acoustic_score.polar_uniformity:.2%}",
                f"- Overall: {self.acoustic_score.overall:.2%}",
            ])

        if self.geometry_metrics:
            lines.extend([
                "",
                "### Geometry Metrics",
                f"- Volume: {self.geometry_metrics.volume_mm3:,.0f} mm³",
                f"- Surface Area: {self.geometry_metrics.surface_area_mm2:,.0f} mm²",
                f"- Fractal Dimension: {self.geometry_metrics.fractal_dimension:.3f}",
                f"- Expansion Ratio: {self.geometry_metrics.expansion_ratio:.2f}",
            ])

        if self.artifacts:
            lines.extend([
                "",
                "### Artifacts",
            ])
            for art in self.artifacts:
                lines.append(f"- [{art.artifact_type.value}] {art.path or 'embedded'}")

        if self.errors:
            lines.extend([
                "",
                "### Errors",
            ])
            for err in self.errors:
                lines.append(f"- {err}")

        if self.execution_time_seconds:
            lines.append(f"\n**Execution Time:** {self.execution_time_seconds:.2f}s")

        return "\n".join(lines)
