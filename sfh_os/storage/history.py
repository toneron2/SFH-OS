"""Iteration History - SQLite-based persistence for project state."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import aiosqlite

from sfh_os.config import config

logger = logging.getLogger(__name__)


class IterationHistory:
    """SQLite-based storage for iteration history and project state.

    Provides persistence for:
    - Project metadata
    - Iteration records
    - Manifest storage
    - Conflict history
    """

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or config.storage.db_path
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Initialize the database and create tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = await aiosqlite.connect(self.db_path)
        await self._create_tables()
        logger.info(f"Database initialized at {self.db_path}")

    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        assert self._connection is not None

        await self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                target_specs TEXT,
                constraints TEXT,
                final_result TEXT
            );

            CREATE TABLE IF NOT EXISTS iterations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                iteration_number INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                phase_reached TEXT,
                success INTEGER DEFAULT 0,
                geometry_result TEXT,
                simulation_result TEXT,
                fabrication_result TEXT,
                verification_result TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS manifests (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                iteration_number INTEGER,
                manifest_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                data TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS conflicts (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                iteration_number INTEGER,
                conflict_type TEXT NOT NULL,
                source_agent TEXT,
                target_agent TEXT,
                description TEXT,
                resolved INTEGER DEFAULT 0,
                resolution_action TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                iteration_number INTEGER,
                artifact_type TEXT NOT NULL,
                file_path TEXT,
                data TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            CREATE INDEX IF NOT EXISTS idx_iterations_project ON iterations(project_id);
            CREATE INDEX IF NOT EXISTS idx_manifests_project ON manifests(project_id);
            CREATE INDEX IF NOT EXISTS idx_conflicts_project ON conflicts(project_id);
            CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);
        """)
        await self._connection.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def create_project(
        self,
        project_id: UUID,
        target_specs: dict[str, Any],
        constraints: dict[str, Any],
    ) -> None:
        """Create a new project record."""
        assert self._connection is not None

        now = datetime.utcnow().isoformat()
        await self._connection.execute(
            """
            INSERT INTO projects (id, created_at, updated_at, target_specs, constraints)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(project_id),
                now,
                now,
                json.dumps(target_specs),
                json.dumps(constraints),
            ),
        )
        await self._connection.commit()
        logger.debug(f"Created project record: {project_id}")

    async def save_iteration(
        self,
        project_id: UUID,
        iteration_number: int,
        started_at: datetime,
        completed_at: datetime | None,
        phase_reached: str,
        success: bool,
        geometry_result: dict[str, Any] | None = None,
        simulation_result: dict[str, Any] | None = None,
        fabrication_result: dict[str, Any] | None = None,
        verification_result: dict[str, Any] | None = None,
    ) -> None:
        """Save an iteration record."""
        assert self._connection is not None

        await self._connection.execute(
            """
            INSERT OR REPLACE INTO iterations
            (project_id, iteration_number, started_at, completed_at, phase_reached,
             success, geometry_result, simulation_result, fabrication_result, verification_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(project_id),
                iteration_number,
                started_at.isoformat(),
                completed_at.isoformat() if completed_at else None,
                phase_reached,
                1 if success else 0,
                json.dumps(geometry_result) if geometry_result else None,
                json.dumps(simulation_result) if simulation_result else None,
                json.dumps(fabrication_result) if fabrication_result else None,
                json.dumps(verification_result) if verification_result else None,
            ),
        )
        await self._connection.commit()

    async def save_manifest(
        self,
        manifest_id: UUID,
        project_id: UUID,
        iteration_number: int | None,
        manifest_type: str,
        data: dict[str, Any],
    ) -> None:
        """Save a manifest to the database."""
        assert self._connection is not None

        await self._connection.execute(
            """
            INSERT INTO manifests (id, project_id, iteration_number, manifest_type, created_at, data)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(manifest_id),
                str(project_id),
                iteration_number,
                manifest_type,
                datetime.utcnow().isoformat(),
                json.dumps(data),
            ),
        )
        await self._connection.commit()

    async def save_conflict(
        self,
        conflict_id: UUID,
        project_id: UUID,
        iteration_number: int | None,
        conflict_type: str,
        source_agent: str,
        target_agent: str,
        description: str,
        resolved: bool = False,
        resolution_action: str | None = None,
    ) -> None:
        """Save a conflict record."""
        assert self._connection is not None

        await self._connection.execute(
            """
            INSERT INTO conflicts
            (id, project_id, iteration_number, conflict_type, source_agent, target_agent,
             description, resolved, resolution_action, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(conflict_id),
                str(project_id),
                iteration_number,
                conflict_type,
                source_agent,
                target_agent,
                description,
                1 if resolved else 0,
                resolution_action,
                datetime.utcnow().isoformat(),
            ),
        )
        await self._connection.commit()

    async def get_project(self, project_id: UUID) -> dict[str, Any] | None:
        """Retrieve a project record."""
        assert self._connection is not None

        async with self._connection.execute(
            "SELECT * FROM projects WHERE id = ?",
            (str(project_id),),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "created_at": row[1],
                    "updated_at": row[2],
                    "status": row[3],
                    "target_specs": json.loads(row[4]) if row[4] else None,
                    "constraints": json.loads(row[5]) if row[5] else None,
                    "final_result": json.loads(row[6]) if row[6] else None,
                }
        return None

    async def get_iterations(self, project_id: UUID) -> list[dict[str, Any]]:
        """Retrieve all iterations for a project."""
        assert self._connection is not None

        iterations = []
        async with self._connection.execute(
            "SELECT * FROM iterations WHERE project_id = ? ORDER BY iteration_number",
            (str(project_id),),
        ) as cursor:
            async for row in cursor:
                iterations.append({
                    "iteration_number": row[2],
                    "started_at": row[3],
                    "completed_at": row[4],
                    "phase_reached": row[5],
                    "success": bool(row[6]),
                    "geometry_result": json.loads(row[7]) if row[7] else None,
                    "simulation_result": json.loads(row[8]) if row[8] else None,
                    "fabrication_result": json.loads(row[9]) if row[9] else None,
                    "verification_result": json.loads(row[10]) if row[10] else None,
                })
        return iterations

    async def update_project_status(
        self,
        project_id: UUID,
        status: str,
        final_result: dict[str, Any] | None = None,
    ) -> None:
        """Update project status."""
        assert self._connection is not None

        await self._connection.execute(
            """
            UPDATE projects
            SET status = ?, updated_at = ?, final_result = ?
            WHERE id = ?
            """,
            (
                status,
                datetime.utcnow().isoformat(),
                json.dumps(final_result) if final_result else None,
                str(project_id),
            ),
        )
        await self._connection.commit()
