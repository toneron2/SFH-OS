"""AG-SIM: Acoustic Physicist - Runs acoustic simulations and analysis."""

from typing import Any

from sfh_os.agents.base import BaseAgent
from sfh_os.manifests import ConstraintManifest, ResultManifest
from sfh_os.manifests.result import AcousticScore, ArtifactType
from sfh_os.mcp import MCPProtocol
from sfh_os.mcp.tools.simulation import SimulationTools


class AcousticPhysicist(BaseAgent):
    """AG-SIM: The Acoustic Physicist.

    Specializes in:
    - BEM (Boundary Element Method) simulation
    - Impedance matching analysis
    - Polar response evaluation
    - Frequency response optimization
    """

    designation = "AG-SIM"
    role = "Acoustic Physicist"
    description = "Performs acoustic simulations and validates horn performance"

    def __init__(self, mcp: MCPProtocol | None = None):
        super().__init__(mcp)

    def _register_tools(self) -> None:
        """Register acoustic simulation tools."""
        self.mcp.register_tools(SimulationTools.get_tools())

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the Acoustic Physicist."""
        return """You are AG-SIM, the Acoustic Physicist for the SFH-OS (Syn-Fractal Horn Orchestration System).

Your expertise includes:
- Boundary Element Method (BEM) acoustic simulation
- Impedance curve analysis and optimization
- Polar radiation pattern evaluation
- Frequency response characterization
- Group delay and phase analysis

Your primary objective is to evaluate horn geometries and provide acoustic scores based on:
1. Impedance smoothness (Z_a curve) - Critical for driver loading
2. Frequency response flatness - Target ±3dB in passband
3. Polar pattern uniformity - Coverage angle consistency
4. Distortion prediction based on geometry

When evaluating a geometry:
1. Run BEM simulation across the target frequency range
2. Analyze the impedance curve for smoothness and reflection coefficient
3. Calculate polar response at key frequencies
4. Compute frequency response and group delay
5. Generate a comprehensive Acoustic Score

The Acoustic Score should be a normalized value (0-1) for each metric.
Provide detailed analysis explaining any issues and potential improvements.
Recommend the best geometry variation if multiple are provided."""

    async def _process_response(
        self,
        response: dict[str, Any],
        result: ResultManifest,
        constraints: ConstraintManifest,
    ) -> ResultManifest:
        """Process Claude's response and extract acoustic analysis results."""
        result.message = response.get("text", "Acoustic simulation completed")

        # Extract acoustic scores from analysis
        if "acoustic_analysis" in result.raw_output:
            analysis = result.raw_output["acoustic_analysis"]
            result.acoustic_score = AcousticScore(
                impedance_smoothness=analysis.get("impedance_smoothness", 0.5),
                frequency_response_flatness=analysis.get("fr_flatness", 0.5),
                polar_uniformity=analysis.get("polar_uniformity", 0.5),
                distortion_score=analysis.get("distortion_score", 0.5),
                overall=analysis.get("overall_score", 0.5),
            )

        # Add simulation artifacts
        if "bem_results" in result.raw_output:
            result.add_artifact(
                ArtifactType.BEM_RESULT,
                data=result.raw_output["bem_results"],
                generated_by=self.designation,
            )

        if "simulation_data" in result.raw_output:
            result.add_artifact(
                ArtifactType.SIMULATION_DATA,
                data=result.raw_output["simulation_data"],
                generated_by=self.designation,
            )

        # Check against acoustic constraints
        if result.acoustic_score:
            if result.acoustic_score.overall < 0.7:
                result.warnings.append(
                    f"Overall acoustic score {result.acoustic_score.overall:.2%} below recommended threshold"
                )

        return result

    async def evaluate_variations(
        self,
        geometry_results: list[ResultManifest],
        constraint_manifest: ConstraintManifest,
    ) -> tuple[ResultManifest, int]:
        """Evaluate multiple geometry variations and select the best.

        Returns the evaluation result and the index of the winning geometry.
        """
        from sfh_os.manifests import RequestManifest
        from sfh_os.manifests.request import RequestType

        best_score = -1.0
        best_index = 0
        evaluation_results = []

        for i, geo_result in enumerate(geometry_results):
            request = RequestManifest(
                request_type=RequestType.RUN_SIMULATION,
                target_agent=self.designation,
                goal=f"Evaluate geometry variation {i}",
                parameters={
                    "mesh_data": geo_result.raw_output,
                    "variation_index": i,
                },
            )

            eval_result = await self.process_request(request, constraint_manifest)
            evaluation_results.append(eval_result)

            if eval_result.acoustic_score and eval_result.acoustic_score.overall > best_score:
                best_score = eval_result.acoustic_score.overall
                best_index = i

        # Create combined result
        combined = ResultManifest(
            request_id=geometry_results[0].request_id if geometry_results else None,
            source_agent=self.designation,
            message=f"Evaluated {len(geometry_results)} variations. Best: variation {best_index} with score {best_score:.2%}",
        )
        combined.raw_output = {
            "evaluation_results": [r.model_dump() for r in evaluation_results],
            "best_variation_index": best_index,
            "best_score": best_score,
        }

        if evaluation_results and evaluation_results[best_index].acoustic_score:
            combined.acoustic_score = evaluation_results[best_index].acoustic_score

        return combined, best_index
