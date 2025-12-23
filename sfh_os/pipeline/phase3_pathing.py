"""Phase 3: Figur-G15 Pathing - Manufacturing preparation."""

import logging
from dataclasses import dataclass

from sfh_os.agents import FabricationEngineer
from sfh_os.manifests import ConstraintManifest, ResultManifest

logger = logging.getLogger(__name__)


@dataclass
class PathingConfig:
    """Configuration for the pathing phase."""

    layer_height_mm: float = 0.2
    forming_speed_mm_s: float = 50.0
    tool_diameter_mm: float = 6.0
    machine_profile: str = "figur_g15"


class FigurPathing:
    """Phase 3: Figur-G15 Pathing.

    AG-MFG prepares the geometry for manufacturing:
    - Analyzes printability
    - Optimizes skin thickness
    - Generates DSF toolpaths
    - Produces validated G-code
    """

    def __init__(self, agent: FabricationEngineer, config: PathingConfig | None = None):
        self.agent = agent
        self.config = config or PathingConfig()

    async def execute(
        self,
        geometry_result: ResultManifest,
        constraints: ConstraintManifest,
    ) -> ResultManifest:
        """Execute the fabrication preparation phase.

        Returns the fabrication result with G-code and toolpaths.
        """
        logger.info("Phase 3: Preparing geometry for manufacturing")

        # Update constraints with pathing config
        constraints.manufacturing.layer_height_mm = self.config.layer_height_mm

        fabrication_result = await self.agent.prepare_for_manufacturing(
            geometry_result, constraints
        )

        # Log results
        if fabrication_result.raw_output.get("manufacturing_ready", False):
            logger.info("Phase 3 complete: Geometry ready for manufacturing")
        else:
            logger.warning("Phase 3 complete: Geometry requires modification")
            for warning in fabrication_result.warnings:
                logger.warning(f"  - {warning}")

        return fabrication_result

    def get_phase_info(self) -> dict:
        """Get information about this phase."""
        return {
            "phase": 3,
            "name": "Figur-G15 Pathing",
            "agent": self.agent.designation,
            "config": {
                "layer_height_mm": self.config.layer_height_mm,
                "forming_speed_mm_s": self.config.forming_speed_mm_s,
                "tool_diameter_mm": self.config.tool_diameter_mm,
                "machine_profile": self.config.machine_profile,
            },
        }
