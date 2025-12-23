"""Constraint Manifest - Defines boundaries for sub-agent operations."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ConstraintType(str, Enum):
    """Types of constraints that can be applied."""

    DIMENSIONAL = "dimensional"
    MATERIAL = "material"
    MANUFACTURING = "manufacturing"
    ACOUSTIC = "acoustic"
    BUDGET = "budget"
    TIME = "time"


class DimensionalConstraints(BaseModel):
    """Physical dimension constraints."""

    max_width_mm: float = Field(default=300.0, ge=10)
    max_height_mm: float = Field(default=300.0, ge=10)
    max_depth_mm: float = Field(default=400.0, ge=10)
    min_wall_thickness_mm: float = Field(default=1.5, ge=0.5)
    max_wall_thickness_mm: float = Field(default=5.0, ge=1.0)
    throat_diameter_mm: float = Field(default=25.4, ge=10)  # 1 inch default
    mouth_diameter_mm: float | None = None


class MaterialConstraints(BaseModel):
    """Material property constraints."""

    material_type: str = Field(default="aluminum")
    density_kg_m3: float = Field(default=2700.0)
    yield_strength_mpa: float = Field(default=276.0)
    thermal_conductivity: float = Field(default=205.0)
    max_operating_temp_c: float = Field(default=150.0)


class ManufacturingConstraints(BaseModel):
    """Manufacturing process constraints."""

    process: str = Field(default="DSF")  # Digital Sheet Forming
    max_build_volume_mm3: float = Field(default=27_000_000)  # 300mm³
    min_feature_size_mm: float = Field(default=0.5)
    max_overhang_angle_deg: float = Field(default=45.0)
    support_allowed: bool = Field(default=False)
    max_print_time_hours: float | None = None
    layer_height_mm: float = Field(default=0.2)


class AcousticConstraints(BaseModel):
    """Acoustic performance constraints."""

    min_sensitivity_db: float = Field(default=100.0)
    max_frequency_response_deviation_db: float = Field(default=3.0)
    target_impedance_ohms: float = Field(default=8.0)
    max_group_delay_ms: float = Field(default=2.0)


class ConstraintManifest(BaseModel):
    """Constraint Manifest for agent communication.

    Contains the boundaries within which a sub-agent must operate.
    """

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    request_id: UUID = Field(description="Associated request manifest ID")
    constraint_types: list[ConstraintType] = Field(default_factory=list)
    dimensional: DimensionalConstraints = Field(default_factory=DimensionalConstraints)
    material: MaterialConstraints = Field(default_factory=MaterialConstraints)
    manufacturing: ManufacturingConstraints = Field(default_factory=ManufacturingConstraints)
    acoustic: AcousticConstraints = Field(default_factory=AcousticConstraints)
    custom_constraints: dict[str, Any] = Field(default_factory=dict)
    strict: bool = Field(default=True, description="If True, constraints are hard limits")

    def to_prompt(self) -> str:
        """Convert manifest to a prompt section for the LLM agent."""
        return f"""## Constraint Manifest
**ID:** {self.id}
**Mode:** {"Strict (hard limits)" if self.strict else "Advisory (soft limits)"}

### Dimensional Constraints
- Max Dimensions: {self.dimensional.max_width_mm}×{self.dimensional.max_height_mm}×{self.dimensional.max_depth_mm} mm
- Wall Thickness: {self.dimensional.min_wall_thickness_mm}-{self.dimensional.max_wall_thickness_mm} mm
- Throat Diameter: {self.dimensional.throat_diameter_mm} mm

### Material Constraints
- Material: {self.material.material_type}
- Density: {self.material.density_kg_m3} kg/m³
- Yield Strength: {self.material.yield_strength_mpa} MPa

### Manufacturing Constraints
- Process: {self.manufacturing.process}
- Max Build Volume: {self.manufacturing.max_build_volume_mm3:,.0f} mm³
- Min Feature Size: {self.manufacturing.min_feature_size_mm} mm
- Max Overhang: {self.manufacturing.max_overhang_angle_deg}°
- Supports: {"Allowed" if self.manufacturing.support_allowed else "Not Allowed"}

### Acoustic Constraints
- Min Sensitivity: {self.acoustic.min_sensitivity_db} dB
- Max FR Deviation: ±{self.acoustic.max_frequency_response_deviation_db} dB
- Target Impedance: {self.acoustic.target_impedance_ohms} Ω
- Max Group Delay: {self.acoustic.max_group_delay_ms} ms

{self._format_custom_constraints()}
"""

    def _format_custom_constraints(self) -> str:
        if not self.custom_constraints:
            return ""
        lines = ["### Custom Constraints"]
        for k, v in self.custom_constraints.items():
            lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    def validate_against(self, result: dict[str, Any]) -> list[str]:
        """Validate a result against these constraints.

        Returns a list of constraint violations (empty if valid).
        """
        violations = []

        # Check dimensional constraints
        if "dimensions" in result:
            dims = result["dimensions"]
            if dims.get("width", 0) > self.dimensional.max_width_mm:
                violations.append(f"Width exceeds maximum: {dims['width']} > {self.dimensional.max_width_mm}")
            if dims.get("height", 0) > self.dimensional.max_height_mm:
                violations.append(f"Height exceeds maximum: {dims['height']} > {self.dimensional.max_height_mm}")

        # Check acoustic constraints
        if "acoustic" in result:
            acoustic = result["acoustic"]
            if acoustic.get("sensitivity_db", 0) < self.acoustic.min_sensitivity_db:
                violations.append(f"Sensitivity below minimum: {acoustic['sensitivity_db']} < {self.acoustic.min_sensitivity_db}")

        return violations
