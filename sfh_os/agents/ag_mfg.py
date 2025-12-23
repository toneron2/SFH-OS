"""AG-MFG: Fabrication Engineer - Handles manufacturing preparation."""

from typing import Any

from sfh_os.agents.base import BaseAgent
from sfh_os.manifests import ConstraintManifest, ResultManifest
from sfh_os.manifests.result import ArtifactType
from sfh_os.mcp import MCPProtocol
from sfh_os.mcp.tools.fabrication import FabricationTools


class FabricationEngineer(BaseAgent):
    """AG-MFG: The Fabrication Engineer.

    Specializes in:
    - Digital Sheet Forming (DSF) logic
    - G-code optimization
    - Toolpath generation for Figur G15-style machines
    - Printability analysis
    """

    designation = "AG-MFG"
    role = "Fabrication Engineer"
    description = "Prepares geometries for manufacturing with optimized toolpaths"

    def __init__(self, mcp: MCPProtocol | None = None):
        super().__init__(mcp)

    def _register_tools(self) -> None:
        """Register fabrication tools."""
        self.mcp.register_tools(FabricationTools.get_tools())

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the Fabrication Engineer."""
        return """You are AG-MFG, the Fabrication Engineer for the SFH-OS (Syn-Fractal Horn Orchestration System).

Your expertise includes:
- Digital Sheet Forming (DSF) process optimization
- G-code generation and optimization
- Toolpath planning for metalforming machines
- Printability analysis for support-free manufacturing
- Material cost estimation

Your primary objective is to prepare horn geometries for manufacturing:
1. Analyze printability - identify overhangs, thin walls, islands
2. Optimize skin thickness for acoustic and structural requirements
3. Generate efficient DSF toolpaths for Figur G15-style machines
4. Produce validated, production-ready G-code

When processing a geometry:
1. First run printability analysis to identify issues
2. If geometry needs modification, suggest specific changes
3. Optimize wall thickness considering acoustic damping needs
4. Generate toolpath with optimal layer strategy
5. Produce and validate G-code
6. Estimate material usage and cost

Critical constraints:
- NO SUPPORTS - Design must be self-supporting
- Fractal edges must be printable at the specified resolution
- Maintain structural integrity during forming process

Report any issues that would prevent successful manufacturing."""

    async def _process_response(
        self,
        response: dict[str, Any],
        result: ResultManifest,
        constraints: ConstraintManifest,
    ) -> ResultManifest:
        """Process Claude's response and extract fabrication results."""
        result.message = response.get("text", "Fabrication preparation completed")

        # Check printability
        if "printability" in result.raw_output:
            printability = result.raw_output["printability"]
            if not printability.get("is_printable_without_supports", True):
                result.warnings.append(
                    f"Geometry requires modification: {printability.get('overhang_percentage', 0):.1f}% overhang"
                )

        # Add G-code artifact if generated
        if "gcode_data" in result.raw_output:
            gcode = result.raw_output["gcode_data"]
            result.add_artifact(
                ArtifactType.GCODE,
                data=gcode,
                generated_by=self.designation,
                estimated_time_hours=gcode.get("estimated_print_time_hours"),
            )

        # Add cost estimation
        if "cost_estimate" in result.raw_output:
            cost = result.raw_output["cost_estimate"]
            result.raw_output["material_cost"] = cost.get("total_material_cost", 0)
            result.raw_output["mass_kg"] = cost.get("mass_kg", 0)

        return result

    async def prepare_for_manufacturing(
        self,
        geometry_result: ResultManifest,
        constraint_manifest: ConstraintManifest,
    ) -> ResultManifest:
        """Complete manufacturing preparation pipeline.

        This method runs the full preparation sequence:
        1. Printability analysis
        2. Skin optimization
        3. Toolpath generation
        4. G-code generation and validation
        """
        from sfh_os.manifests import RequestManifest
        from sfh_os.manifests.request import RequestType

        request = RequestManifest(
            request_type=RequestType.GENERATE_TOOLPATH,
            target_agent=self.designation,
            goal="Prepare geometry for manufacturing",
            parameters={
                "mesh_data": geometry_result.raw_output,
                "geometry_metrics": geometry_result.geometry_metrics.model_dump()
                if geometry_result.geometry_metrics
                else {},
            },
        )

        result = await self.process_request(request, constraint_manifest)

        # Add manufacturing readiness assessment
        is_ready = (
            len(result.errors) == 0
            and all("requires modification" not in w.lower() for w in result.warnings)
        )
        result.raw_output["manufacturing_ready"] = is_ready

        return result
