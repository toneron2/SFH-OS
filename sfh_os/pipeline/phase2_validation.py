"""Phase 2: Acoustic Validation - Evaluate geometry variations."""

import logging
from dataclasses import dataclass

from sfh_os.agents import AcousticPhysicist
from sfh_os.manifests import ConstraintManifest, ResultManifest

logger = logging.getLogger(__name__)


@dataclass
class ValidationConfig:
    """Configuration for the validation phase."""

    min_acceptable_score: float = 0.7
    run_full_simulation: bool = True
    include_polar_analysis: bool = True


class AcousticValidation:
    """Phase 2: Acoustic Validation.

    AG-SIM evaluates geometry variations through acoustic simulation
    and selects the best performing design.
    """

    def __init__(self, agent: AcousticPhysicist, config: ValidationConfig | None = None):
        self.agent = agent
        self.config = config or ValidationConfig()

    async def execute(
        self,
        geometry_variations: list[ResultManifest],
        constraints: ConstraintManifest,
    ) -> tuple[ResultManifest, ResultManifest]:
        """Execute the acoustic validation phase.

        Returns:
            tuple: (evaluation_result, best_geometry)
        """
        logger.info(f"Phase 2: Evaluating {len(geometry_variations)} geometry variations")

        if not geometry_variations:
            raise ValueError("No geometry variations to evaluate")

        evaluation_result, best_index = await self.agent.evaluate_variations(
            geometry_variations, constraints
        )

        best_geometry = geometry_variations[best_index]

        # Log results
        if evaluation_result.acoustic_score:
            score = evaluation_result.acoustic_score.overall
            logger.info(f"Phase 2 complete: Best variation {best_index} with score {score:.2%}")

            if score < self.config.min_acceptable_score:
                logger.warning(f"Score {score:.2%} below threshold {self.config.min_acceptable_score:.2%}")

        return evaluation_result, best_geometry

    def get_phase_info(self) -> dict:
        """Get information about this phase."""
        return {
            "phase": 2,
            "name": "Acoustic Validation",
            "agent": self.agent.designation,
            "config": {
                "min_acceptable_score": self.config.min_acceptable_score,
                "run_full_simulation": self.config.run_full_simulation,
                "include_polar_analysis": self.config.include_polar_analysis,
            },
        }
