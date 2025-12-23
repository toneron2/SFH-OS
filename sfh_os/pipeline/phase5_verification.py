"""Phase 5: Verification - Post-print quality assurance."""

import logging
from dataclasses import dataclass

from sfh_os.agents import QualityVerification
from sfh_os.manifests import ConstraintManifest, ResultManifest

logger = logging.getLogger(__name__)


@dataclass
class VerificationConfig:
    """Configuration for the verification phase."""

    tolerance_db: float = 3.0
    run_visual_inspection: bool = True
    run_acoustic_sweep: bool = True
    run_impedance_measurement: bool = True


class Verification:
    """Phase 5: Verification.

    AG-QA performs post-manufacturing verification:
    - Visual inspection for defects
    - Acoustic sine sweep testing
    - Comparison to simulation predictions
    - Generation of verification report
    """

    def __init__(self, agent: QualityVerification, config: VerificationConfig | None = None):
        self.agent = agent
        self.config = config or VerificationConfig()

    async def execute(
        self,
        simulation_result: ResultManifest,
        constraints: ConstraintManifest,
    ) -> ResultManifest:
        """Execute the verification phase.

        Returns the verification result with pass/fail status.
        """
        logger.info("Phase 5: Running verification suite")

        verification_result = await self.agent.run_full_verification(
            simulation_result, constraints
        )

        # Log results
        overall = verification_result.raw_output.get("overall_result", "UNKNOWN")
        logger.info(f"Phase 5 complete: {overall}")

        if overall == "FAIL":
            logger.warning("Verification failed - iteration may be needed")
            for error in verification_result.errors:
                logger.warning(f"  - {error}")

        return verification_result

    async def generate_final_package(
        self,
        geometry_result: ResultManifest,
        simulation_result: ResultManifest,
        fabrication_result: ResultManifest,
        verification_result: ResultManifest,
    ) -> ResultManifest:
        """Generate the final production package.

        Called when verification passes successfully.
        """
        logger.info("Generating final production package")

        package = await self.agent.generate_production_package(
            geometry_result,
            simulation_result,
            fabrication_result,
            verification_result,
        )

        logger.info("Production package generated successfully")
        return package

    def get_phase_info(self) -> dict:
        """Get information about this phase."""
        return {
            "phase": 5,
            "name": "Verification",
            "agent": self.agent.designation,
            "config": {
                "tolerance_db": self.config.tolerance_db,
                "run_visual_inspection": self.config.run_visual_inspection,
                "run_acoustic_sweep": self.config.run_acoustic_sweep,
                "run_impedance_measurement": self.config.run_impedance_measurement,
            },
        }
