"""Project job persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from core.services.projects.repository import utc_now


@dataclass(frozen=True, slots=True)
class ProjectJobRecord:
    job_id: str
    type: str
    status: str
    progress: float
    message: str
    resource_type: str
    resource_id: int
    created_at: str
    updated_at: str
    result: dict[str, Any] | None
    error: dict[str, Any] | None


class ProjectJobStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_job(
        self,
        *,
        project_id: int,
        job_type: str,
        status: str,
        progress: float,
        message: str,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> ProjectJobRecord:
        job_id = f"job_{uuid4().hex}"
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, type, status, progress, message, resource_type,
                    resource_id, result, error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    job_type,
                    status,
                    progress,
                    message,
                    "Project",
                    project_id,
                    json.dumps(result, ensure_ascii=False) if result is not None else None,
                    json.dumps(error, ensure_ascii=False) if error is not None else None,
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> ProjectJobRecord:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(f"Job not found: {job_id}")
        return self._job_from_row(row)

    def list_recent(self, *, project_id: int, limit: int = 5) -> list[ProjectJobRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM jobs
                WHERE resource_type = ? AND resource_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                ("Project", project_id, limit),
            ).fetchall()
        return [self._job_from_row(row) for row in rows]

    def _job_from_row(self, row: sqlite3.Row) -> ProjectJobRecord:
        return ProjectJobRecord(
            job_id=str(row["job_id"]),
            type=str(row["type"]),
            status=str(row["status"]),
            progress=float(row["progress"]),
            message=str(row["message"]),
            resource_type=str(row["resource_type"]),
            resource_id=int(row["resource_id"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            result=json.loads(row["result"]) if row["result"] else None,
            error=json.loads(row["error"]) if row["error"] else None,
        )
