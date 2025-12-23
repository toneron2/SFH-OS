"""AG-QA: Quality/Verification - Handles post-manufacturing verification."""

from typing import Any

from sfh_os.agents.base import BaseAgent
from sfh_os.manifests import ConstraintManifest, ResultManifest
from sfh_os.manifests.result import ArtifactType
from sfh_os.mcp import MCPProtocol
from sfh_os.mcp.tools.verification import VerificationTools


class QualityVerification(BaseAgent):
    """AG-QA: Quality and Verification.

    Specializes in:
    - Automated visual inspection
    - Acoustic sweep analysis
    - Simulation vs. reality comparison
    - Comprehensive verification reporting
    """

    designation = "AG-QA"
    role = "Quality/Verification"
    description = "Verifies manufactured horns against design specifications"

    def __init__(self, mcp: MCPProtocol | None = None):
        super().__init__(mcp)

    def _register_tools(self) -> None:
        """Register verification tools."""
        self.mcp.register_tools(VerificationTools.get_tools())

    def _get_system_prompt(self) -> str:
        """Get the system prompt for Quality Verification."""
        return """You are AG-QA, the Quality and Verification agent for the SFH-OS (Syn-Fractal Horn Orchestration System).

Your expertise includes:
- Automated visual inspection using computer vision
- Acoustic measurement and analysis (sine sweeps, impedance)
- Comparison of measured results to simulation predictions
- Generation of comprehensive verification reports

Your primary objective is to verify that manufactured horns meet specifications:
1. Visual inspection for surface defects, dimensional accuracy
2. Acoustic measurement via sine sweep testing
3. Impedance measurement to verify driver loading
4. Comparison against simulation predictions

Verification criteria:
- Surface defects: None above minor severity
- Dimensional accuracy: ±0.5mm from design
- Acoustic deviation: ±3dB from simulation
- Impedance: Within 10% of predicted values

When verifying a horn:
1. Run visual inspection first - stop if major defects found
2. Perform acoustic sine sweep measurement
3. Measure electrical impedance
4. Compare all measurements to simulation predictions
5. Generate comprehensive verification report

The verification report should include:
- Pass/Fail status for each test
- Detailed measurements and deviations
- Side-by-side comparison plots
- Recommendations for any issues found
- Certification readiness assessment"""

    async def _process_response(
        self,
        response: dict[str, Any],
        result: ResultManifest,
        constraints: ConstraintManifest,
    ) -> ResultManifest:
        """Process Claude's response and extract verification results."""
        result.message = response.get("text", "Verification completed")

        # Check verification status
        if "verification_report" in result.raw_output:
            report = result.raw_output["verification_report"]
            result.raw_output["overall_result"] = report.get("overall_result", "UNKNOWN")
            result.raw_output["certification_ready"] = report.get("certification_ready", False)

            if report.get("overall_result") == "FAIL":
                result.errors.append("Verification failed - see report for details")
                for rec in report.get("recommendations", []):
                    result.warnings.append(f"Recommendation: {rec}")

        # Add report artifact
        if "verification_report" in result.raw_output:
            result.add_artifact(
                ArtifactType.REPORT,
                data=result.raw_output["verification_report"],
                generated_by=self.designation,
                report_type="verification",
            )

        return result

    async def run_full_verification(
        self,
        simulation_results: ResultManifest,
        constraint_manifest: ConstraintManifest,
    ) -> ResultManifest:
        """Run complete verification suite.

        This method orchestrates the full verification process:
        1. Visual inspection
        2. Acoustic sine sweep
        3. Impedance measurement
        4. Comparison to simulation
        5. Report generation
        """
        from sfh_os.manifests import RequestManifest
        from sfh_os.manifests.request import RequestType

        request = RequestManifest(
            request_type=RequestType.RUN_VERIFICATION,
            target_agent=self.designation,
            goal="Run complete verification suite",
            parameters={
                "simulation_results": simulation_results.raw_output,
                "acoustic_score": simulation_results.acoustic_score.model_dump()
                if simulation_results.acoustic_score
                else {},
            },
        )

        result = await self.process_request(request, constraint_manifest)

        # Determine if iteration is needed
        needs_iteration = (
            result.raw_output.get("overall_result") == "FAIL"
            or not result.raw_output.get("certification_ready", False)
        )
        result.raw_output["needs_iteration"] = needs_iteration

        return result

    async def generate_production_package(
        self,
        geometry_result: ResultManifest,
        simulation_result: ResultManifest,
        fabrication_result: ResultManifest,
        verification_result: ResultManifest,
    ) -> ResultManifest:
        """Generate the final production package.

        The production package includes:
        - Digital Twin (AKABAK model)
        - Assembly Manual
        - Verification Report
        """
        from sfh_os.manifests.result import ResultStatus

        result = ResultManifest(
            request_id=verification_result.request_id,
            source_agent=self.designation,
        )

        # Compile production package
        package = {
            "physical_horn": {
                "geometry": geometry_result.geometry_metrics.model_dump()
                if geometry_result.geometry_metrics
                else {},
                "material": "high-density metal",
                "gcode_file": fabrication_result.raw_output.get("gcode_data", {}).get("checksum"),
            },
            "digital_twin": {
                "simulation_data": simulation_result.raw_output,
                "acoustic_score": simulation_result.acoustic_score.model_dump()
                if simulation_result.acoustic_score
                else {},
            },
            "assembly_manual": {
                "driver_mounting": "See attached instructions",
                "dampening_application": "Apply acoustic foam to rear chamber",
                "wiring": "Connect driver to crossover as specified",
            },
            "verification_report": verification_result.raw_output,
        }

        result.raw_output = {"production_package": package}
        result.message = "Production package generated successfully"

        result.add_artifact(
            ArtifactType.REPORT,
            data=package,
            generated_by=self.designation,
            report_type="production_package",
        )

        result.mark_complete(ResultStatus.SUCCESS)
        return result
