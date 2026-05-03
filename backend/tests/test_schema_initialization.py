from __future__ import annotations

import sqlite3
from pathlib import Path

from core.schema import PROJECT_SCHEMA_SQL


def test_project_schema_initializes_core_platform_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "research_flow.sqlite"

    with sqlite3.connect(db_path) as conn:
        conn.executescript(PROJECT_SCHEMA_SQL)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {
        "physical_item",
        "asset_registry",
        "asset_link",
        "biz_doc_layout",
        "jobs",
        "biz_paper",
        "biz_paper_artifact",
        "biz_paper_pipeline_run",
        "biz_note_state",
        "biz_knowledge",
        "biz_dataset",
        "biz_category",
        "biz_project",
        "biz_presentation",
        "sys_agent_profile",
        "sys_skill_binding",
        "sys_llm_probe_result",
    } <= tables
