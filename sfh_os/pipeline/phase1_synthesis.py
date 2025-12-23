"""Phase 1: Generative Synthesis - Create fractal geometry variations."""

import logging
from dataclasses import dataclass

from sfh_os.agents import FractalArchitect
from sfh_os.manifests import ConstraintManifest, RequestManifest, ResultManifest

logger = logging.getLogger(__name__)


@dataclass
class SynthesisConfig:
    """Configuration for the synthesis phase."""

    num_variations: int = 3
    fractal_approaches: list[str] | None = None

    def __post_init__(self):
        if self.fractal_approaches is None:
            self.fractal_approaches = ["hilbert", "peano", "mandelbrot"]


class GenerativeSynthesis:
    """Phase 1: Generative Synthesis.

    AG-GEN creates fractal geometry variations based on target specifications.
    Multiple variations are generated to give the Acoustic Physicist options.
    """

    def __init__(self, agent: FractalArchitect, config: SynthesisConfig | None = None):
        self.agent = agent
        self.config = config or SynthesisConfig()

    async def execute(
        self,
        request: RequestManifest,
        constraints: ConstraintManifest,
    ) -> list[ResultManifest]:
        """Execute the generative synthesis phase.

        Returns a list of geometry variations for evaluation.
        """
        logger.info(f"Phase 1: Generating {self.config.num_variations} fractal variations")

        variations = await self.agent.generate_variations(
            request,
            constraints,
            num_variations=self.config.num_variations,
        )

        successful = [v for v in variations if v.status != "failed"]
        logger.info(f"Phase 1 complete: {len(successful)}/{len(variations)} successful")

        return variations

    def get_phase_info(self) -> dict:
        """Get information about this phase."""
        return {
            "phase": 1,
            "name": "Generative Synthesis",
            "agent": self.agent.designation,
            "config": {
                "num_variations": self.config.num_variations,
                "approaches": self.config.fractal_approaches,
            },
        }
