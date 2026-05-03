from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from core.config import Settings, get_settings
from core.schema import BASE_SCHEMA_SQL
from core.services.papers.models import utc_now
from core.services.system_config.models import (
    AgentProfileRecord,
    ConfigConflictError,
    ConfigNotFoundError,
    LLMProbeResultRecord,
    SkillBindingRecord,
    SkillCatalogRecord,
)
from core.storage import configured_db_path


class SystemConfigRepository:
    def __init__(
        self,
        db_path: Path | None = None,
        skills_root: Path | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db_path = db_path or configured_db_path()
        self.skills_root = skills_root or self._default_skills_root()
        self.settings = settings or get_settings()
        self.initialize()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(BASE_SCHEMA_SQL)
            self._seed_agent_profiles(conn)
            self._seed_skill_bindings(conn)
            self._seed_probe_results(conn)
            conn.commit()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_agents(self) -> list[AgentProfileRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT profile_key, scene, provider, model_name, temperature,
                    max_tokens, enabled, updated_at
                FROM sys_agent_profile
                ORDER BY scene ASC, profile_key ASC
                """
            ).fetchall()
        return [self._agent_from_row(row) for row in rows]

    def get_agent(self, profile_key: str) -> AgentProfileRecord:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT profile_key, scene, provider, model_name, temperature,
                    max_tokens, enabled, updated_at
                FROM sys_agent_profile
                WHERE profile_key = ?
                """,
                (profile_key,),
            ).fetchone()
        if row is None:
            raise ConfigNotFoundError(f"Agent profile not found: {profile_key}")
        return self._agent_from_row(row)

    def update_agent(
        self,
        profile_key: str,
        values: dict[str, Any],
    ) -> AgentProfileRecord:
        self.get_agent(profile_key)
        allowed = {
            "scene",
            "provider",
            "model_name",
            "temperature",
            "max_tokens",
            "enabled",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        if not updates:
            raise ConfigConflictError("No supported agent profile fields provided.")
        if "enabled" in updates:
            updates["enabled"] = 1 if updates["enabled"] else 0
        updates["updated_at"] = utc_now()
        columns = [f"{key} = ?" for key in updates]
        with self.connect() as conn:
            conn.execute(
                f"""
                UPDATE sys_agent_profile
                SET {', '.join(columns)}
                WHERE profile_key = ?
                """,
                [*updates.values(), profile_key],
            )
            self._upsert_probe_from_agent(conn, profile_key)
            conn.commit()
        return self.get_agent(profile_key)

    def list_skill_catalog(self) -> list[SkillCatalogRecord]:
        if not self.skills_root.exists():
            return []
        records = [
            self._catalog_from_skill_dir(skill_dir)
            for skill_dir in sorted(self.skills_root.iterdir(), key=lambda item: item.name)
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists()
        ]
        return records

    def get_skill_catalog_item(self, skill_name: str) -> SkillCatalogRecord:
        skill_dir = self.skills_root / skill_name
        if not (skill_dir / "SKILL.md").exists():
            raise ConfigNotFoundError(f"Skill not found: {skill_name}")
        return self._catalog_from_skill_dir(skill_dir)

    def list_skill_bindings(self) -> list[SkillBindingRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT skill_key, scene, agent_profile_key, runtime_instruction_key,
                    toolset_json, enabled, updated_at
                FROM sys_skill_binding
                ORDER BY scene ASC, skill_key ASC
                """
            ).fetchall()
        return [self._skill_binding_from_row(row) for row in rows]

    def get_skill_binding(self, skill_key: str) -> SkillBindingRecord:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT skill_key, scene, agent_profile_key, runtime_instruction_key,
                    toolset_json, enabled, updated_at
                FROM sys_skill_binding
                WHERE skill_key = ?
                """,
                (skill_key,),
            ).fetchone()
        if row is None:
            raise ConfigNotFoundError(f"Skill binding not found: {skill_key}")
        return self._skill_binding_from_row(row)

    def update_skill_binding(
        self,
        skill_key: str,
        values: dict[str, Any],
    ) -> SkillBindingRecord:
        self.get_skill_binding(skill_key)
        allowed = {
            "scene",
            "agent_profile_key",
            "runtime_instruction_key",
            "toolset",
            "enabled",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        if "agent_profile_key" in updates:
            self.get_agent(str(updates["agent_profile_key"]))
        if "toolset" in updates:
            updates["toolset_json"] = json.dumps(
                updates.pop("toolset"),
                ensure_ascii=False,
            )
        if "enabled" in updates:
            updates["enabled"] = 1 if updates["enabled"] else 0
        updates["updated_at"] = utc_now()
        columns = [f"{key} = ?" for key in updates]
        with self.connect() as conn:
            conn.execute(
                f"""
                UPDATE sys_skill_binding
                SET {', '.join(columns)}
                WHERE skill_key = ?
                """,
                [*updates.values(), skill_key],
            )
            conn.commit()
        return self.get_skill_binding(skill_key)

    def list_llm_status(self) -> list[LLMProbeResultRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT profile_key, provider, model_name, connectivity_status,
                    ttft_ms, checked_at, error_message
                FROM sys_llm_probe_result
                ORDER BY profile_key ASC
                """
            ).fetchall()
        return [self._probe_from_row(row) for row in rows]

    def _seed_agent_profiles(self, conn: sqlite3.Connection) -> None:
        now = utc_now()
        for feature_key, feature in self.settings.llm.features.items():
            model = self.settings.llm.models.get(feature.model_key)
            if model is None:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO sys_agent_profile (
                    profile_key, scene, provider, model_name, temperature,
                    max_tokens, enabled, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feature_key,
                    feature_key,
                    model.platform,
                    model.model_id,
                    feature.temperature
                    if feature.temperature is not None
                    else model.temperature,
                    feature.max_tokens
                    if feature.max_tokens is not None
                    else model.max_tokens,
                    1 if model.enabled else 0,
                    now,
                ),
            )

    def _seed_skill_bindings(self, conn: sqlite3.Connection) -> None:
        default_profile = self.settings.llm.default_feature or self._first_profile_key(conn)
        if default_profile is None:
            return
        now = utc_now()
        for item in self.list_skill_catalog():
            conn.execute(
                """
                INSERT OR IGNORE INTO sys_skill_binding (
                    skill_key, scene, agent_profile_key, runtime_instruction_key,
                    toolset_json, enabled, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.skill_name,
                    item.skill_name,
                    default_profile,
                    "",
                    "[]",
                    1,
                    now,
                ),
            )

    def _seed_probe_results(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(
            """
            SELECT profile_key
            FROM sys_agent_profile
            """
        ).fetchall()
        for row in rows:
            self._upsert_probe_from_agent(conn, str(row["profile_key"]))

    def _upsert_probe_from_agent(
        self,
        conn: sqlite3.Connection,
        profile_key: str,
    ) -> None:
        row = conn.execute(
            """
            SELECT profile_key, provider, model_name, enabled
            FROM sys_agent_profile
            WHERE profile_key = ?
            """,
            (profile_key,),
        ).fetchone()
        if row is None:
            return
        status = "not_checked" if int(row["enabled"]) else "disabled"
        now = utc_now()
        conn.execute(
            """
            INSERT INTO sys_llm_probe_result (
                profile_key, provider, model_name, connectivity_status,
                ttft_ms, probe_started_at, checked_at, error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_key) DO UPDATE SET
                provider = excluded.provider,
                model_name = excluded.model_name,
                connectivity_status = excluded.connectivity_status,
                ttft_ms = excluded.ttft_ms,
                checked_at = excluded.checked_at,
                error_message = excluded.error_message
            """,
            (
                profile_key,
                str(row["provider"]),
                str(row["model_name"]),
                status,
                None,
                None,
                now,
                "",
            ),
        )

    def _first_profile_key(self, conn: sqlite3.Connection) -> str | None:
        row = conn.execute(
            """
            SELECT profile_key
            FROM sys_agent_profile
            ORDER BY profile_key ASC
            LIMIT 1
            """
        ).fetchone()
        return None if row is None else str(row["profile_key"])

    def _catalog_from_skill_dir(self, skill_dir: Path) -> SkillCatalogRecord:
        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        description = self._front_matter_value(content, "description")
        return SkillCatalogRecord(
            skill_name=skill_dir.name,
            description=description,
            path=str(skill_dir),
            has_runtime_instructions=(
                skill_dir / "references" / "runtime-instructions.md"
            ).exists(),
            has_agent_metadata=(skill_dir / "agents" / "openai.yaml").exists(),
        )

    def _front_matter_value(self, content: str, key: str) -> str:
        match = re.search(rf"^{key}:\s*(.+)$", content, flags=re.MULTILINE)
        return "" if match is None else match.group(1).strip().strip('"')

    def _default_skills_root(self) -> Path:
        return Path(__file__).resolve().parents[4] / "skills"

    def _agent_from_row(self, row: sqlite3.Row) -> AgentProfileRecord:
        return AgentProfileRecord(
            profile_key=str(row["profile_key"]),
            scene=str(row["scene"]),
            provider=str(row["provider"]),
            model_name=str(row["model_name"]),
            temperature=row["temperature"],
            max_tokens=row["max_tokens"],
            enabled=bool(row["enabled"]),
            updated_at=str(row["updated_at"]),
        )

    def _skill_binding_from_row(self, row: sqlite3.Row) -> SkillBindingRecord:
        return SkillBindingRecord(
            skill_key=str(row["skill_key"]),
            scene=str(row["scene"]),
            agent_profile_key=str(row["agent_profile_key"]),
            runtime_instruction_key=str(row["runtime_instruction_key"] or ""),
            toolset=json.loads(row["toolset_json"] or "[]"),
            enabled=bool(row["enabled"]),
            updated_at=str(row["updated_at"]),
        )

    def _probe_from_row(self, row: sqlite3.Row) -> LLMProbeResultRecord:
        return LLMProbeResultRecord(
            profile_key=str(row["profile_key"]),
            provider=str(row["provider"]),
            model_name=str(row["model_name"]),
            connectivity_status=str(row["connectivity_status"]),
            ttft_ms=row["ttft_ms"],
            checked_at=str(row["checked_at"]),
            error_message=str(row["error_message"] or ""),
        )
