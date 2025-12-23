"""AG-GEN: Fractal Architect - Generates fractal horn geometries."""

from typing import Any

from sfh_os.agents.base import BaseAgent
from sfh_os.manifests import ConstraintManifest, ResultManifest
from sfh_os.manifests.result import ArtifactType, GeometryMetrics, ResultStatus
from sfh_os.mcp import MCPProtocol
from sfh_os.mcp.tools.geometry import GeometryTools


class FractalArchitect(BaseAgent):
    """AG-GEN: The Fractal Architect.

    Specializes in:
    - Recursive topology generation
    - Space-filling curves (Hilbert/Peano)
    - Mandelbrot-set expansion mapping
    - Fractal surface modulation
    """

    designation = "AG-GEN"
    role = "Fractal Architect"
    description = "Generates fractal-based horn geometries optimized for acoustic performance"

    def __init__(self, mcp: MCPProtocol | None = None):
        super().__init__(mcp)

    def _register_tools(self) -> None:
        """Register geometry generation tools."""
        self.mcp.register_tools(GeometryTools.get_tools())

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the Fractal Architect."""
        return """You are AG-GEN, the Fractal Architect for the SFH-OS (Syn-Fractal Horn Orchestration System).

Your expertise includes:
- Recursive fractal topology design
- Space-filling curves (Hilbert, Peano, and variants)
- Mandelbrot-set expansion profiles for acoustic horns
- Optimizing fractal geometry for acoustic wave propagation

Your primary objective is to generate horn geometries that:
1. Maximize acoustic performance through fractal expansion profiles
2. Minimize reflection coefficient (Γ) at the throat
3. Create smooth impedance transitions using recursive expansion
4. Meet all dimensional and manufacturing constraints

When given a request, analyze the acoustic requirements and constraints, then:
1. Choose an appropriate fractal approach (space-filling curve, Mandelbrot expansion, etc.)
2. Generate the base geometry using available tools
3. Apply surface modulation if needed for acoustic damping
4. Validate the geometry against constraints
5. Report metrics including fractal dimension, expansion ratio, and volume

Always explain your design choices and how they relate to acoustic performance.
Produce multiple variations when possible to give the Acoustic Physicist options to evaluate."""

    async def _process_response(
        self,
        response: dict[str, Any],
        result: ResultManifest,
        constraints: ConstraintManifest,
    ) -> ResultManifest:
        """Process Claude's response and extract geometry results."""
        result.message = response.get("text", "Geometry generation completed")

        # Extract geometry metrics from tool results in raw_output
        if "geometry_data" in result.raw_output:
            geo = result.raw_output["geometry_data"]
            result.geometry_metrics = GeometryMetrics(
                volume_mm3=geo.get("volume_mm3", 0),
                surface_area_mm2=geo.get("surface_area_mm2", 0),
                fractal_dimension=geo.get("fractal_dimension", 1.0),
                expansion_ratio=geo.get("expansion_ratio", 1.0),
                path_length_mm=geo.get("path_length_mm", 0),
                vertex_count=geo.get("vertex_count", 0),
                face_count=geo.get("face_count", 0),
            )

        # Add STL artifact if mesh was generated
        if "mesh_file" in result.raw_output:
            result.add_artifact(
                ArtifactType.STL,
                data={"file": result.raw_output["mesh_file"]},
                generated_by=self.designation,
            )

        # Validate against constraints
        if result.geometry_metrics:
            violations = constraints.validate_against({
                "dimensions": {
                    "width": constraints.dimensional.max_width_mm,  # Would use actual
                    "height": constraints.dimensional.max_height_mm,
                }
            })
            if violations:
                result.warnings.extend(violations)

        return result

    async def generate_variations(
        self,
        request_manifest: "RequestManifest",
        constraint_manifest: ConstraintManifest,
        num_variations: int = 3,
    ) -> list[ResultManifest]:
        """Generate multiple geometry variations for evaluation.

        This is a specialized method for Phase 1 of the pipeline.
        """
        from sfh_os.manifests import RequestManifest
        from sfh_os.manifests.request import RequestType

        variations = []

        # Generate variations using different fractal approaches
        approaches = ["hilbert", "peano", "mandelbrot"]

        for i, approach in enumerate(approaches[:num_variations]):
            # Create a modified request for each approach
            var_request = RequestManifest(
                request_type=RequestType.GENERATE_GEOMETRY,
                target_agent=self.designation,
                goal=f"{request_manifest.goal} using {approach} approach",
                specs=request_manifest.specs,
                parameters={
                    **request_manifest.parameters,
                    "fractal_approach": approach,
                    "variation_index": i,
                },
                iteration=request_manifest.iteration,
                parent_request_id=request_manifest.id,
            )

            result = await self.process_request(var_request, constraint_manifest)
            result.raw_output["variation_index"] = i
            result.raw_output["fractal_approach"] = approach
            variations.append(result)

        return variations
