from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any


SCHEMA_VERSION = 3


@dataclass(frozen=True)
class WorkspaceRow:
    workspace_id: str
    name: str
    attach_type: str
    attach_config: dict[str, Any]
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class EventRow:
    event_id: int
    workspace_id: str
    ts: int
    level: str
    event_type: str
    message: str
    data: dict[str, Any]


@dataclass(frozen=True)
class JobRow:
    job_id: str
    workspace_id: str
    kind: str
    name: str
    status: str
    created_at: int
    started_at: int
    finished_at: int
    progress_current: int
    progress_total: int
    message: str
    data: dict[str, Any]


@dataclass(frozen=True)
class JobStepRow:
    step_id: int
    job_id: str
    ts: int
    level: str
    step_index: int
    step_name: str
    event_type: str
    message: str
    data: dict[str, Any]


@dataclass(frozen=True)
class ArtifactRow:
    artifact_id: str
    job_id: str
    workspace_id: str
    name: str
    kind: str
    path: str
    size_bytes: int
    created_at: int


@dataclass(frozen=True)
class SnapshotRow:
    snapshot_id: int
    workspace_id: str
    ts: int
    snapshot_type: str
    data: dict[str, Any]


class SeedOpsStore:
    """SQLite persistence for SeedOps (workspaces + events)."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _init_db(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA foreign_keys=OFF;")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    attach_type TEXT NOT NULL,
                    attach_config_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id TEXT NOT NULL,
                    ts INTEGER NOT NULL,
                    level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data_json TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_ws_ts ON events(workspace_id, ts DESC)")

            # schema version bootstrap
            cur.execute("SELECT version FROM schema_version LIMIT 1")
            row = cur.fetchone()
            if row is None:
                # New DB: start at version 0 and apply migrations to SCHEMA_VERSION.
                cur.execute("INSERT INTO schema_version(version) VALUES (0)")
                current_version = 0
            else:
                current_version = int(row["version"])

            # Migrations
            if current_version < 2:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        workspace_id TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        started_at INTEGER NOT NULL,
                        finished_at INTEGER NOT NULL,
                        progress_current INTEGER NOT NULL,
                        progress_total INTEGER NOT NULL,
                        message TEXT NOT NULL,
                        data_json TEXT NOT NULL
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_ws_created ON jobs(workspace_id, created_at DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at DESC)")

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS job_steps (
                        step_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        ts INTEGER NOT NULL,
                        level TEXT NOT NULL,
                        step_index INTEGER NOT NULL,
                        step_name TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        data_json TEXT NOT NULL
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_job_steps_job_step ON job_steps(job_id, step_id DESC)")

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS artifacts (
                        artifact_id TEXT PRIMARY KEY,
                        job_id TEXT NOT NULL,
                        workspace_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        path TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        created_at INTEGER NOT NULL
                    )
                    """
                )
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_artifacts_job_name ON artifacts(job_id, name)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_ws_created ON artifacts(workspace_id, created_at DESC)")

                current_version = 2

            if current_version < 3:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS snapshots (
                        snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        workspace_id TEXT NOT NULL,
                        ts INTEGER NOT NULL,
                        snapshot_type TEXT NOT NULL,
                        data_json TEXT NOT NULL
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_ws_ts ON snapshots(workspace_id, ts DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_type_ts ON snapshots(snapshot_type, ts DESC)")
                current_version = 3

            # Persist schema version
            cur.execute("UPDATE schema_version SET version = ?", (current_version,))

            self._conn.commit()

    def _row_to_workspace(self, row: sqlite3.Row) -> WorkspaceRow:
        attach_config = json.loads(row["attach_config_json"]) if row["attach_config_json"] else {}
        return WorkspaceRow(
            workspace_id=row["workspace_id"],
            name=row["name"],
            attach_type=row["attach_type"],
            attach_config=attach_config,
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
        )

    def _row_to_event(self, row: sqlite3.Row) -> EventRow:
        data = json.loads(row["data_json"]) if row["data_json"] else {}
        return EventRow(
            event_id=int(row["event_id"]),
            workspace_id=row["workspace_id"],
            ts=int(row["ts"]),
            level=row["level"],
            event_type=row["event_type"],
            message=row["message"],
            data=data,
        )

    def _row_to_job(self, row: sqlite3.Row) -> JobRow:
        data = json.loads(row["data_json"]) if row["data_json"] else {}
        return JobRow(
            job_id=row["job_id"],
            workspace_id=row["workspace_id"],
            kind=row["kind"],
            name=row["name"],
            status=row["status"],
            created_at=int(row["created_at"]),
            started_at=int(row["started_at"]),
            finished_at=int(row["finished_at"]),
            progress_current=int(row["progress_current"]),
            progress_total=int(row["progress_total"]),
            message=row["message"],
            data=data,
        )

    def _row_to_job_step(self, row: sqlite3.Row) -> JobStepRow:
        data = json.loads(row["data_json"]) if row["data_json"] else {}
        return JobStepRow(
            step_id=int(row["step_id"]),
            job_id=row["job_id"],
            ts=int(row["ts"]),
            level=row["level"],
            step_index=int(row["step_index"]),
            step_name=row["step_name"],
            event_type=row["event_type"],
            message=row["message"],
            data=data,
        )

    def _row_to_artifact(self, row: sqlite3.Row) -> ArtifactRow:
        return ArtifactRow(
            artifact_id=row["artifact_id"],
            job_id=row["job_id"],
            workspace_id=row["workspace_id"],
            name=row["name"],
            kind=row["kind"],
            path=row["path"],
            size_bytes=int(row["size_bytes"]),
            created_at=int(row["created_at"]),
        )

    def _row_to_snapshot(self, row: sqlite3.Row) -> SnapshotRow:
        data = json.loads(row["data_json"]) if row["data_json"] else {}
        return SnapshotRow(
            snapshot_id=int(row["snapshot_id"]),
            workspace_id=row["workspace_id"],
            ts=int(row["ts"]),
            snapshot_type=row["snapshot_type"],
            data=data,
        )

    def create_workspace(self, name: str) -> WorkspaceRow:
        now = int(time.time())
        workspace_id = str(uuid.uuid4())
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO workspaces(workspace_id, name, attach_type, attach_config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (workspace_id, name, "compose", "{}", now, now),
            )
            self._conn.commit()
        return WorkspaceRow(
            workspace_id=workspace_id,
            name=name,
            attach_type="compose",
            attach_config={},
            created_at=now,
            updated_at=now,
        )

    def list_workspaces(self) -> list[WorkspaceRow]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT workspace_id, name, attach_type, attach_config_json, created_at, updated_at FROM workspaces ORDER BY name"
            )
            rows = cur.fetchall()
        return [self._row_to_workspace(r) for r in rows]

    def get_workspace(self, workspace_id: str) -> WorkspaceRow | None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT workspace_id, name, attach_type, attach_config_json, created_at, updated_at FROM workspaces WHERE workspace_id = ?",
                (workspace_id,),
            )
            row = cur.fetchone()
        return self._row_to_workspace(row) if row else None

    def update_workspace_attach(self, workspace_id: str, attach_type: str, attach_config: dict[str, Any]) -> None:
        now = int(time.time())
        attach_config_json = json.dumps(attach_config, separators=(",", ":"), ensure_ascii=False)
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                UPDATE workspaces
                   SET attach_type = ?, attach_config_json = ?, updated_at = ?
                 WHERE workspace_id = ?
                """,
                (attach_type, attach_config_json, now, workspace_id),
            )
            self._conn.commit()

    def insert_event(
        self,
        workspace_id: str,
        *,
        level: str,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> int:
        now = int(time.time())
        payload = json.dumps(data or {}, separators=(",", ":"), ensure_ascii=False)
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO events(workspace_id, ts, level, event_type, message, data_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (workspace_id, now, level, event_type, message, payload),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def list_events(self, workspace_id: str, *, since_ts: int = 0, limit: int = 200) -> list[EventRow]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT event_id, workspace_id, ts, level, event_type, message, data_json
                  FROM events
                 WHERE workspace_id = ?
                   AND ts >= ?
                 ORDER BY ts DESC, event_id DESC
                 LIMIT ?
                """,
                (workspace_id, int(since_ts), int(limit)),
            )
            rows = cur.fetchall()
        return [self._row_to_event(r) for r in rows]

    def create_job(
        self,
        workspace_id: str,
        *,
        kind: str,
        name: str,
        status: str = "queued",
        message: str = "",
        data: dict[str, Any] | None = None,
        progress_total: int = 0,
    ) -> JobRow:
        now = int(time.time())
        job_id = str(uuid.uuid4())
        payload = json.dumps(data or {}, separators=(",", ":"), ensure_ascii=False)
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO jobs(
                    job_id, workspace_id, kind, name, status, created_at, started_at, finished_at,
                    progress_current, progress_total, message, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    workspace_id,
                    kind,
                    name,
                    status,
                    now,
                    0,
                    0,
                    0,
                    int(progress_total),
                    message,
                    payload,
                ),
            )
            self._conn.commit()
        return JobRow(
            job_id=job_id,
            workspace_id=workspace_id,
            kind=kind,
            name=name,
            status=status,
            created_at=now,
            started_at=0,
            finished_at=0,
            progress_current=0,
            progress_total=int(progress_total),
            message=message,
            data=data or {},
        )

    def get_job(self, job_id: str) -> JobRow | None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(self, workspace_id: str, *, status: str | None = None, limit: int = 50) -> list[JobRow]:
        with self._lock:
            cur = self._conn.cursor()
            if status:
                cur.execute(
                    "SELECT * FROM jobs WHERE workspace_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?",
                    (workspace_id, status, int(limit)),
                )
            else:
                cur.execute(
                    "SELECT * FROM jobs WHERE workspace_id = ? ORDER BY created_at DESC LIMIT ?",
                    (workspace_id, int(limit)),
                )
            rows = cur.fetchall()
        return [self._row_to_job(r) for r in rows]

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        message: str | None = None,
        progress_current: int | None = None,
        progress_total: int | None = None,
        started_at: int | None = None,
        finished_at: int | None = None,
    ) -> None:
        fields: list[str] = []
        args: list[Any] = []
        if status is not None:
            fields.append("status = ?")
            args.append(status)
        if message is not None:
            fields.append("message = ?")
            args.append(message)
        if progress_current is not None:
            fields.append("progress_current = ?")
            args.append(int(progress_current))
        if progress_total is not None:
            fields.append("progress_total = ?")
            args.append(int(progress_total))
        if started_at is not None:
            fields.append("started_at = ?")
            args.append(int(started_at))
        if finished_at is not None:
            fields.append("finished_at = ?")
            args.append(int(finished_at))
        if not fields:
            return
        args.append(job_id)
        sql = "UPDATE jobs SET " + ", ".join(fields) + " WHERE job_id = ?"
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, tuple(args))
            self._conn.commit()

    def mark_running_jobs_interrupted(self) -> int:
        """Mark any jobs left in 'running' as 'interrupted' (e.g. after server restart)."""
        now = int(time.time())
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                UPDATE jobs
                   SET status = ?, finished_at = ?, message = ?
                 WHERE status = ?
                """,
                ("interrupted", now, "server restarted", "running"),
            )
            self._conn.commit()
            return int(cur.rowcount or 0)

    def insert_job_step(
        self,
        job_id: str,
        *,
        level: str,
        step_index: int,
        step_name: str,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> int:
        now = int(time.time())
        payload = json.dumps(data or {}, separators=(",", ":"), ensure_ascii=False)
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO job_steps(job_id, ts, level, step_index, step_name, event_type, message, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, now, level, int(step_index), step_name, event_type, message, payload),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def list_job_steps(self, job_id: str, *, since_step_id: int = 0, limit: int = 200) -> list[JobStepRow]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT * FROM job_steps
                 WHERE job_id = ?
                   AND step_id > ?
                 ORDER BY step_id ASC
                 LIMIT ?
                """,
                (job_id, int(since_step_id), int(limit)),
            )
            rows = cur.fetchall()
        return [self._row_to_job_step(r) for r in rows]

    def insert_artifact(
        self,
        *,
        artifact_id: str,
        job_id: str,
        workspace_id: str,
        name: str,
        kind: str,
        path: str,
        size_bytes: int,
    ) -> None:
        now = int(time.time())
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO artifacts(artifact_id, job_id, workspace_id, name, kind, path, size_bytes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (artifact_id, job_id, workspace_id, name, kind, path, int(size_bytes), now),
            )
            self._conn.commit()

    def list_artifacts(self, job_id: str, *, limit: int = 200) -> list[ArtifactRow]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM artifacts WHERE job_id = ? ORDER BY created_at DESC LIMIT ?", (job_id, int(limit)))
            rows = cur.fetchall()
        return [self._row_to_artifact(r) for r in rows]

    def get_artifact(self, artifact_id: str) -> ArtifactRow | None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,))
            row = cur.fetchone()
        return self._row_to_artifact(row) if row else None

    def insert_snapshot(self, workspace_id: str, *, snapshot_type: str, data: dict[str, Any] | None = None) -> int:
        now = int(time.time())
        payload = json.dumps(data or {}, separators=(",", ":"), ensure_ascii=False)
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO snapshots(workspace_id, ts, snapshot_type, data_json)
                VALUES (?, ?, ?, ?)
                """,
                (workspace_id, now, snapshot_type, payload),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def list_snapshots(
        self,
        workspace_id: str,
        *,
        snapshot_type: str | None = None,
        since_ts: int = 0,
        limit: int = 200,
    ) -> list[SnapshotRow]:
        with self._lock:
            cur = self._conn.cursor()
            if snapshot_type:
                cur.execute(
                    """
                    SELECT * FROM snapshots
                     WHERE workspace_id = ?
                       AND snapshot_type = ?
                       AND ts >= ?
                     ORDER BY ts DESC, snapshot_id DESC
                     LIMIT ?
                    """,
                    (workspace_id, snapshot_type, int(since_ts), int(limit)),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM snapshots
                     WHERE workspace_id = ?
                       AND ts >= ?
                     ORDER BY ts DESC, snapshot_id DESC
                     LIMIT ?
                    """,
                    (workspace_id, int(since_ts), int(limit)),
                )
            rows = cur.fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    def prune_events(self, workspace_id: str, *, keep_last: int = 5000) -> int:
        keep = int(keep_last)
        with self._lock:
            cur = self._conn.cursor()
            if keep <= 0:
                cur.execute("DELETE FROM events WHERE workspace_id = ?", (workspace_id,))
                self._conn.commit()
                return int(cur.rowcount or 0)

            cur.execute(
                """
                DELETE FROM events
                 WHERE workspace_id = ?
                   AND event_id NOT IN (
                        SELECT event_id
                          FROM events
                         WHERE workspace_id = ?
                         ORDER BY ts DESC, event_id DESC
                         LIMIT ?
                   )
                """,
                (workspace_id, workspace_id, keep),
            )
            self._conn.commit()
            return int(cur.rowcount or 0)

    def prune_snapshots(self, workspace_id: str, *, snapshot_type: str | None = None, keep_last: int = 5000) -> int:
        keep = int(keep_last)
        with self._lock:
            cur = self._conn.cursor()
            if keep <= 0:
                if snapshot_type:
                    cur.execute("DELETE FROM snapshots WHERE workspace_id = ? AND snapshot_type = ?", (workspace_id, snapshot_type))
                else:
                    cur.execute("DELETE FROM snapshots WHERE workspace_id = ?", (workspace_id,))
                self._conn.commit()
                return int(cur.rowcount or 0)

            if snapshot_type:
                cur.execute(
                    """
                    DELETE FROM snapshots
                     WHERE workspace_id = ?
                       AND snapshot_type = ?
                       AND snapshot_id NOT IN (
                            SELECT snapshot_id
                              FROM snapshots
                             WHERE workspace_id = ?
                               AND snapshot_type = ?
                             ORDER BY ts DESC, snapshot_id DESC
                             LIMIT ?
                       )
                    """,
                    (workspace_id, snapshot_type, workspace_id, snapshot_type, keep),
                )
            else:
                cur.execute(
                    """
                    DELETE FROM snapshots
                     WHERE workspace_id = ?
                       AND snapshot_id NOT IN (
                            SELECT snapshot_id
                              FROM snapshots
                             WHERE workspace_id = ?
                             ORDER BY ts DESC, snapshot_id DESC
                             LIMIT ?
                       )
                    """,
                    (workspace_id, workspace_id, keep),
                )
            self._conn.commit()
            return int(cur.rowcount or 0)

    def list_terminal_job_ids_to_prune(self, workspace_id: str, *, keep_last: int = 200) -> list[str]:
        keep = int(keep_last)
        terminal = ("succeeded", "failed", "canceled", "interrupted", "succeeded_with_errors")
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                f"""
                SELECT job_id
                  FROM jobs
                 WHERE workspace_id = ?
                   AND status IN ({",".join("?" for _ in terminal)})
                 ORDER BY created_at DESC, job_id DESC
                """,
                (workspace_id, *terminal),
            )
            job_ids = [str(r["job_id"]) for r in cur.fetchall()]
        if keep <= 0:
            return job_ids
        return job_ids[keep:]

    def list_artifacts_for_job_ids(self, job_ids: list[str]) -> list[ArtifactRow]:
        if not job_ids:
            return []
        placeholders = ",".join("?" for _ in job_ids)
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(f"SELECT * FROM artifacts WHERE job_id IN ({placeholders})", tuple(job_ids))
            rows = cur.fetchall()
        return [self._row_to_artifact(r) for r in rows]

    def delete_jobs_and_related(self, job_ids: list[str]) -> dict[str, int]:
        if not job_ids:
            return {"jobs_deleted": 0, "job_steps_deleted": 0, "artifacts_deleted": 0}
        placeholders = ",".join("?" for _ in job_ids)
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(f"DELETE FROM job_steps WHERE job_id IN ({placeholders})", tuple(job_ids))
            steps_deleted = int(cur.rowcount or 0)
            cur.execute(f"DELETE FROM artifacts WHERE job_id IN ({placeholders})", tuple(job_ids))
            artifacts_deleted = int(cur.rowcount or 0)
            cur.execute(f"DELETE FROM jobs WHERE job_id IN ({placeholders})", tuple(job_ids))
            jobs_deleted = int(cur.rowcount or 0)
            self._conn.commit()
        return {
            "jobs_deleted": jobs_deleted,
            "job_steps_deleted": steps_deleted,
            "artifacts_deleted": artifacts_deleted,
        }
