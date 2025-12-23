"""SFH-OS: Syn-Fractal Horn Orchestration System - Main Entry Point."""

import asyncio
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from sfh_os import __version__
from sfh_os.conductor import Conductor
from sfh_os.config import config
from sfh_os.manifests import ConstraintManifest
from sfh_os.manifests.constraint import (
    AcousticConstraints,
    DimensionalConstraints,
    ManufacturingConstraints,
    MaterialConstraints,
)
from sfh_os.manifests.request import FrequencyRange, TargetSpecs
from sfh_os.storage import IterationHistory

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger("sfh_os")


def print_banner() -> None:
    """Print the SFH-OS banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║     _____ ______ _    _         ____   _____                  ║
║    / ____|  ____| |  | |       / __ \ / ____|                 ║
║   | (___ | |__  | |__| |______| |  | | (___                   ║
║    \___ \|  __| |  __  |______| |  | |\___ \                  ║
║    ____) | |    | |  | |      | |__| |____) |                 ║
║   |_____/|_|    |_|  |_|       \____/|_____/                  ║
║                                                               ║
║   Syn-Fractal Horn Orchestration System                       ║
║   Autonomous Agentic Design & Manufacturing Framework         ║
╚═══════════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold blue")
    console.print(f"Version {__version__}\n", style="dim")


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """SFH-OS: Autonomous horn design and manufacturing system."""
    pass


@cli.command()
@click.option(
    "--freq-min",
    default=1000.0,
    help="Minimum frequency in Hz",
    type=float,
)
@click.option(
    "--freq-max",
    default=20000.0,
    help="Maximum frequency in Hz",
    type=float,
)
@click.option(
    "--sensitivity",
    default=105.0,
    help="Target sensitivity in dB",
    type=float,
)
@click.option(
    "--coverage-h",
    default=90.0,
    help="Horizontal coverage angle in degrees",
    type=float,
)
@click.option(
    "--coverage-v",
    default=40.0,
    help="Vertical coverage angle in degrees",
    type=float,
)
@click.option(
    "--max-iterations",
    default=10,
    help="Maximum optimization iterations",
    type=int,
)
@click.option(
    "--output-dir",
    default="./output",
    help="Output directory for artifacts",
    type=click.Path(),
)
def run(
    freq_min: float,
    freq_max: float,
    sensitivity: float,
    coverage_h: float,
    coverage_v: float,
    max_iterations: int,
    output_dir: str,
) -> None:
    """Run a complete horn design project."""
    print_banner()

    # Check API key
    if not config.llm.api_key:
        console.print(
            "[red]Error:[/red] ANTHROPIC_API_KEY environment variable not set",
            style="bold",
        )
        sys.exit(1)

    # Create target specs
    target_specs = TargetSpecs(
        frequency_range=FrequencyRange(min_hz=freq_min, max_hz=freq_max),
        target_sensitivity_db=sensitivity,
        coverage_angle_h=coverage_h,
        coverage_angle_v=coverage_v,
    )

    # Display configuration
    table = Table(title="Project Configuration")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Frequency Range", f"{freq_min:.0f} Hz - {freq_max:.0f} Hz")
    table.add_row("Target Sensitivity", f"{sensitivity:.1f} dB")
    table.add_row("Coverage (H × V)", f"{coverage_h:.0f}° × {coverage_v:.0f}°")
    table.add_row("Max Iterations", str(max_iterations))
    table.add_row("Output Directory", output_dir)

    console.print(table)
    console.print()

    # Run the project
    asyncio.run(_run_project(target_specs, max_iterations, Path(output_dir)))


async def _run_project(
    target_specs: TargetSpecs,
    max_iterations: int,
    output_dir: Path,
) -> None:
    """Run the project asynchronously."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize storage
    history = IterationHistory(output_dir / "history.db")
    await history.initialize()

    # Create conductor
    conductor = Conductor()
    conductor.state.max_iterations = max_iterations

    # Create constraints
    constraints = ConstraintManifest(
        request_id=conductor.state.project_id,
        dimensional=DimensionalConstraints(),
        material=MaterialConstraints(),
        manufacturing=ManufacturingConstraints(),
        acoustic=AcousticConstraints(),
    )

    # Save project to history
    await history.create_project(
        conductor.state.project_id,
        target_specs.model_dump(),
        constraints.model_dump(),
    )

    console.print(
        Panel(
            f"Project ID: {conductor.state.project_id}\n"
            f"Starting optimization with up to {max_iterations} iterations...",
            title="Project Started",
            style="green",
        )
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running pipeline...", total=None)

            # Run the project
            result = await conductor.run_project(target_specs, constraints)

            progress.update(task, description="Complete!")

        # Display results
        console.print()

        if result.status.value == "success":
            console.print(
                Panel(
                    f"Project completed successfully!\n\n"
                    f"Iterations: {conductor.state.current_iteration}\n"
                    f"Best Acoustic Score: {conductor.state.best_acoustic_score:.2%}\n"
                    f"Best Iteration: {conductor.state.best_iteration}",
                    title="Success",
                    style="bold green",
                )
            )
        else:
            console.print(
                Panel(
                    f"Project completed with status: {result.status.value}\n\n"
                    f"Message: {result.message}\n"
                    f"Errors: {', '.join(result.errors) if result.errors else 'None'}",
                    title="Result",
                    style="yellow",
                )
            )

        # Save final state
        await history.update_project_status(
            conductor.state.project_id,
            result.status.value,
            result.model_dump(),
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="bold")
        logger.exception("Project failed")
        sys.exit(1)

    finally:
        await history.close()


@cli.command()
def info() -> None:
    """Display system information."""
    print_banner()

    table = Table(title="System Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("LLM Provider", config.llm.provider)
    table.add_row("Model", config.llm.model)
    table.add_row("API Key Set", "Yes" if config.llm.api_key else "No")
    table.add_row("Max Tokens", str(config.llm.max_tokens))
    table.add_row("Database Path", str(config.storage.db_path))
    table.add_row("Artifacts Path", str(config.storage.artifacts_path))
    table.add_row("Max Iterations", str(config.pipeline.max_iterations))
    table.add_row("Convergence Threshold", f"{config.pipeline.convergence_threshold:.0%}")

    console.print(table)

    # Display agent information
    console.print()
    agent_table = Table(title="Sub-Agents")
    agent_table.add_column("Designation", style="cyan")
    agent_table.add_column("Role", style="green")
    agent_table.add_column("Tools", style="yellow")

    agent_table.add_row("AG-GEN", "Fractal Architect", "Geometry generation")
    agent_table.add_row("AG-SIM", "Acoustic Physicist", "BEM simulation")
    agent_table.add_row("AG-MFG", "Fabrication Engineer", "Toolpath/G-code")
    agent_table.add_row("AG-QA", "Quality/Verification", "Inspection/Testing")

    console.print(agent_table)


@cli.command()
@click.argument("project_id")
@click.option(
    "--db-path",
    default="./output/history.db",
    help="Path to history database",
    type=click.Path(),
)
def status(project_id: str, db_path: str) -> None:
    """Check status of a project."""
    asyncio.run(_check_status(project_id, Path(db_path)))


async def _check_status(project_id: str, db_path: Path) -> None:
    """Check project status asynchronously."""
    from uuid import UUID

    history = IterationHistory(db_path)
    await history.initialize()

    try:
        project = await history.get_project(UUID(project_id))

        if not project:
            console.print(f"[red]Project not found:[/red] {project_id}")
            return

        console.print(Panel(f"Project: {project_id}", style="blue"))

        table = Table()
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Status", project["status"])
        table.add_row("Created", project["created_at"])
        table.add_row("Updated", project["updated_at"])

        console.print(table)

        # Show iterations
        iterations = await history.get_iterations(UUID(project_id))

        if iterations:
            console.print()
            iter_table = Table(title="Iterations")
            iter_table.add_column("#", style="cyan")
            iter_table.add_column("Phase", style="green")
            iter_table.add_column("Success", style="yellow")
            iter_table.add_column("Started", style="dim")

            for it in iterations:
                iter_table.add_row(
                    str(it["iteration_number"]),
                    it["phase_reached"],
                    "Yes" if it["success"] else "No",
                    it["started_at"][:19],
                )

            console.print(iter_table)

    finally:
        await history.close()


if __name__ == "__main__":
    cli()
