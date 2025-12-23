"""Request Manifest - Specifies goals for sub-agents."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RequestType(str, Enum):
    """Types of requests that can be made to sub-agents."""

    GENERATE_GEOMETRY = "generate_geometry"
    OPTIMIZE_THROAT = "optimize_throat"
    RUN_SIMULATION = "run_simulation"
    ANALYZE_IMPEDANCE = "analyze_impedance"
    GENERATE_TOOLPATH = "generate_toolpath"
    OPTIMIZE_SKIN = "optimize_skin"
    EXECUTE_PRINT = "execute_print"
    RUN_VERIFICATION = "run_verification"
    COMPARE_RESULTS = "compare_results"


class FrequencyRange(BaseModel):
    """Frequency range specification."""

    min_hz: float = Field(ge=20, le=20000)
    max_hz: float = Field(ge=20, le=20000)

    def __str__(self) -> str:
        return f"{self.min_hz}Hz-{self.max_hz}Hz"


class TargetSpecs(BaseModel):
    """Target specifications for horn design."""

    frequency_range: FrequencyRange = Field(
        default_factory=lambda: FrequencyRange(min_hz=1000, max_hz=20000)
    )
    target_sensitivity_db: float = Field(default=105.0, ge=80, le=130)
    coverage_angle_h: float = Field(default=90.0, ge=10, le=180)
    coverage_angle_v: float = Field(default=40.0, ge=10, le=180)
    max_distortion_thd: float = Field(default=1.0, ge=0.1, le=10.0)


class RequestManifest(BaseModel):
    """Request Manifest for agent communication.

    Contains the specific goal for a sub-agent to execute.
    """

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    request_type: RequestType
    target_agent: str = Field(description="Agent designation (e.g., AG-GEN, AG-SIM)")
    source_agent: str = Field(default="CONDUCTOR")
    goal: str = Field(description="Human-readable goal description")
    specs: TargetSpecs = Field(default_factory=TargetSpecs)
    parameters: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1, ge=1, le=5)
    iteration: int = Field(default=1, ge=1)
    parent_request_id: UUID | None = None

    def to_prompt(self) -> str:
        """Convert manifest to a prompt for the LLM agent."""
        return f"""## Request Manifest
**ID:** {self.id}
**Type:** {self.request_type.value}
**Goal:** {self.goal}

### Target Specifications
- Frequency Range: {self.specs.frequency_range}
- Target Sensitivity: {self.specs.target_sensitivity_db} dB
- Coverage (H×V): {self.specs.coverage_angle_h}° × {self.specs.coverage_angle_v}°
- Max THD: {self.specs.max_distortion_thd}%

### Parameters
{self._format_parameters()}

### Context
- Iteration: {self.iteration}
- Priority: {self.priority}/5
"""

    def _format_parameters(self) -> str:
        if not self.parameters:
            return "No additional parameters."
        return "\n".join(f"- {k}: {v}" for k, v in self.parameters.items())
