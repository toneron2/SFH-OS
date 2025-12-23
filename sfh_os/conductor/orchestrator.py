"""Conductor - The main orchestration agent for SFH-OS."""

import logging
from typing import Any

import anthropic

from sfh_os.agents import (
    AcousticPhysicist,
    FabricationEngineer,
    FractalArchitect,
    QualityVerification,
)
from sfh_os.config import config
from sfh_os.conductor.state import Conflict, ConflictType, GlobalState, ProjectPhase
from sfh_os.manifests import ConstraintManifest, RequestManifest, ResultManifest
from sfh_os.manifests.request import RequestType, TargetSpecs
from sfh_os.manifests.result import ResultStatus
from sfh_os.mcp import MCPProtocol

logger = logging.getLogger(__name__)


class Conductor:
    """The Conductor - Chief System Architect for SFH-OS.

    The Conductor:
    - Manages the lifecycle of horn design projects
    - Maintains global state across iterations
    - Routes work to appropriate sub-agents
    - Resolves conflicts between acoustic and manufacturing requirements
    - Controls the iteration loop for optimization
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.llm.api_key)
        self.state = GlobalState()
        self.mcp = MCPProtocol()

        # Initialize sub-agents
        self.ag_gen = FractalArchitect(self.mcp)
        self.ag_sim = AcousticPhysicist(self.mcp)
        self.ag_mfg = FabricationEngineer(self.mcp)
        self.ag_qa = QualityVerification(self.mcp)

        # Configuration
        self.convergence_threshold = config.pipeline.convergence_threshold
        self.parallel_variations = config.pipeline.parallel_variations

    async def run_project(
        self,
        target_specs: TargetSpecs,
        constraints: ConstraintManifest | None = None,
    ) -> ResultManifest:
        """Run a complete horn design project.

        This is the main entry point for the Conductor.
        """
        logger.info(f"Starting new project: {self.state.project_id}")

        # Initialize constraints if not provided
        if constraints is None:
            constraints = ConstraintManifest(request_id=self.state.project_id)

        self.state.active_constraints = constraints

        # Create initial request
        initial_request = RequestManifest(
            request_type=RequestType.GENERATE_GEOMETRY,
            target_agent="AG-GEN",
            goal="Design a fractal horn meeting target specifications",
            specs=target_specs,
        )
        self.state.active_request = initial_request

        # Main iteration loop
        final_result = None

        while self.state.should_continue_iterating():
            logger.info(f"Starting iteration {self.state.current_iteration + 1}")
            self.state.start_iteration()

            try:
                result = await self._run_iteration(initial_request, constraints)
                final_result = result

                # Check for successful completion
                if result.status == ResultStatus.SUCCESS:
                    if self._check_convergence(result):
                        logger.info("Convergence achieved!")
                        self.state.set_phase(ProjectPhase.COMPLETE)
                        break

                self.state.complete_iteration(success=result.status == ResultStatus.SUCCESS)

            except Exception as e:
                logger.error(f"Iteration failed: {e}")
                self.state.complete_iteration(success=False)
                self._handle_iteration_failure(str(e))

        # Generate final production package if successful
        if self.state.current_phase == ProjectPhase.COMPLETE and final_result:
            return await self._generate_production_package()

        # Return best result if we hit iteration limit
        if self.state.best_simulation:
            logger.warning(f"Returning best result from iteration {self.state.best_iteration}")
            return self.state.best_simulation

        # Return failure result
        return ResultManifest(
            request_id=initial_request.id,
            source_agent="CONDUCTOR",
            status=ResultStatus.FAILED,
            message=f"Project failed after {self.state.current_iteration} iterations",
            errors=["Maximum iterations reached without convergence"],
        )

    async def _run_iteration(
        self,
        request: RequestManifest,
        constraints: ConstraintManifest,
    ) -> ResultManifest:
        """Run a single iteration through the pipeline."""

        # Phase 1: Generative Synthesis
        self.state.set_phase(ProjectPhase.SYNTHESIS)
        logger.info("Phase 1: Generative Synthesis")

        geometry_variations = await self.ag_gen.generate_variations(
            request, constraints, num_variations=self.parallel_variations
        )
        logger.info(f"Generated {len(geometry_variations)} geometry variations")

        # Phase 2: Acoustic Validation
        self.state.set_phase(ProjectPhase.VALIDATION)
        logger.info("Phase 2: Acoustic Validation")

        simulation_result, best_index = await self.ag_sim.evaluate_variations(
            geometry_variations, constraints
        )
        best_geometry = geometry_variations[best_index]

        self.state.record_geometry_result(best_geometry)
        self.state.record_simulation_result(simulation_result)

        # Check for acoustic/manufacturing conflicts
        await self._check_and_resolve_conflicts(best_geometry, simulation_result)

        # Phase 3: Figur-G15 Pathing
        self.state.set_phase(ProjectPhase.PATHING)
        logger.info("Phase 3: Fabrication Preparation")

        fabrication_result = await self.ag_mfg.prepare_for_manufacturing(
            best_geometry, constraints
        )
        self.state.record_fabrication_result(fabrication_result)

        if not fabrication_result.raw_output.get("manufacturing_ready", False):
            logger.warning("Geometry not manufacturing ready - may need iteration")
            self._add_manufacturing_conflict(fabrication_result)

        # Phase 4: Physical Execution (simulated in stub)
        self.state.set_phase(ProjectPhase.EXECUTION)
        logger.info("Phase 4: Physical Execution (simulated)")

        # In real implementation, this would send to printer and wait
        execution_result = ResultManifest(
            request_id=request.id,
            source_agent="CONDUCTOR",
            status=ResultStatus.SUCCESS,
            message="Physical execution simulated - horn printed successfully",
        )

        # Phase 5: Verification
        self.state.set_phase(ProjectPhase.VERIFICATION)
        logger.info("Phase 5: Verification")

        verification_result = await self.ag_qa.run_full_verification(
            simulation_result, constraints
        )
        self.state.record_verification_result(verification_result)

        # Determine iteration outcome
        if verification_result.raw_output.get("needs_iteration", False):
            logger.info("Verification indicates need for iteration")
            return verification_result

        verification_result.status = ResultStatus.SUCCESS
        return verification_result

    async def _check_and_resolve_conflicts(
        self,
        geometry_result: ResultManifest,
        simulation_result: ResultManifest,
    ) -> None:
        """Check for conflicts between acoustic and manufacturing requirements."""

        # Check if acoustic score is acceptable
        if simulation_result.acoustic_score:
            if simulation_result.acoustic_score.overall < 0.7:
                conflict = Conflict(
                    conflict_type=ConflictType.ACOUSTIC_MANUFACTURING_TRADEOFF,
                    source_agent="AG-SIM",
                    target_agent="AG-GEN",
                    description=f"Acoustic score {simulation_result.acoustic_score.overall:.2%} below threshold",
                    proposed_resolution="Adjust fractal parameters for better acoustic performance",
                )
                self.state.add_conflict(conflict)

        # Check for geometry constraint violations
        if geometry_result.warnings:
            for warning in geometry_result.warnings:
                if "exceeds" in warning.lower() or "violation" in warning.lower():
                    conflict = Conflict(
                        conflict_type=ConflictType.CONSTRAINT_VIOLATION,
                        source_agent="AG-GEN",
                        target_agent="CONDUCTOR",
                        description=warning,
                    )
                    self.state.add_conflict(conflict)

    def _add_manufacturing_conflict(self, fabrication_result: ResultManifest) -> None:
        """Add a manufacturing conflict based on fabrication result."""
        for warning in fabrication_result.warnings:
            conflict = Conflict(
                conflict_type=ConflictType.ACOUSTIC_MANUFACTURING_TRADEOFF,
                source_agent="AG-MFG",
                target_agent="AG-GEN",
                description=warning,
                proposed_resolution="Modify geometry to improve printability",
            )
            self.state.add_conflict(conflict)

    def _check_convergence(self, result: ResultManifest) -> bool:
        """Check if the optimization has converged."""
        if not result.acoustic_score:
            return False

        # Check if we've achieved target score
        if result.acoustic_score.overall >= self.convergence_threshold:
            return True

        # Check if we've plateaued (no improvement in last 3 iterations)
        if len(self.state.iterations) >= 3:
            recent_scores = []
            for iteration in self.state.iterations[-3:]:
                if iteration.simulation_result and iteration.simulation_result.acoustic_score:
                    recent_scores.append(iteration.simulation_result.acoustic_score.overall)

            if len(recent_scores) == 3:
                improvement = max(recent_scores) - min(recent_scores)
                if improvement < 0.01:  # Less than 1% improvement
                    logger.info("Convergence detected: plateau in scores")
                    return True

        return False

    def _handle_iteration_failure(self, error: str) -> None:
        """Handle a failed iteration."""
        conflict = Conflict(
            conflict_type=ConflictType.ITERATION_LIMIT,
            source_agent="CONDUCTOR",
            target_agent="CONDUCTOR",
            description=f"Iteration failed: {error}",
        )
        self.state.add_conflict(conflict)

    async def _generate_production_package(self) -> ResultManifest:
        """Generate the final production package."""
        logger.info("Generating production package")

        if not all([
            self.state.best_geometry,
            self.state.best_simulation,
        ]):
            return ResultManifest(
                request_id=self.state.project_id,
                source_agent="CONDUCTOR",
                status=ResultStatus.FAILED,
                message="Cannot generate production package: missing required results",
            )

        # Get the latest results from the successful iteration
        current = self.state.current_iteration_record

        return await self.ag_qa.generate_production_package(
            geometry_result=self.state.best_geometry,
            simulation_result=self.state.best_simulation,
            fabrication_result=current.fabrication_result if current else ResultManifest(
                request_id=self.state.project_id,
                source_agent="AG-MFG",
            ),
            verification_result=current.verification_result if current else ResultManifest(
                request_id=self.state.project_id,
                source_agent="AG-QA",
            ),
        )

    def get_state_summary(self) -> dict[str, Any]:
        """Get current project state summary."""
        return self.state.get_summary()
