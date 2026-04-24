"""共享 SQLite schema 片段。

当前仍是轻量 sqlite3 落地，先把 Paper 与 Project 共同使用的表结构集中到
core，后续可平滑替换为 ORM/Alembic。
"""

from __future__ import annotations


# 资产层、文档映射和 Job 表是多个业务模块共同依赖的基础表。
BASE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS physical_item (
    item_id TEXT PRIMARY KEY,
    storage_path TEXT NOT NULL,
    storage_type TEXT NOT NULL DEFAULT 'LOCAL',
    ref_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS asset_registry (
    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    file_ext TEXT NOT NULL DEFAULT '',
    file_size INTEGER NOT NULL DEFAULT 0,
    content_hash TEXT NOT NULL DEFAULT '',
    asset_type TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES physical_item(item_id)
);

CREATE TABLE IF NOT EXISTS asset_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES asset_registry(asset_id),
    FOREIGN KEY (target_id) REFERENCES asset_registry(asset_id)
);

CREATE TABLE IF NOT EXISTS biz_doc_layout (
    map_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER NOT NULL,
    doc_id INTEGER NOT NULL,
    doc_name TEXT NOT NULL,
    doc_path TEXT NOT NULL,
    doc_role TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (parent_id, doc_role),
    FOREIGN KEY (parent_id) REFERENCES asset_registry(asset_id),
    FOREIGN KEY (doc_id) REFERENCES asset_registry(asset_id)
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL NOT NULL,
    message TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id INTEGER NOT NULL,
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_asset_registry_type ON asset_registry(asset_type);
CREATE INDEX IF NOT EXISTS idx_asset_registry_deleted ON asset_registry(is_deleted);
CREATE INDEX IF NOT EXISTS idx_asset_link_source ON asset_link(source_id);
CREATE INDEX IF NOT EXISTS idx_asset_link_target ON asset_link(target_id);
CREATE INDEX IF NOT EXISTS idx_biz_doc_layout_parent ON biz_doc_layout(parent_id);
"""


# Paper 现有主链路继续复用这份 schema，保持历史 API 行为不变。
PAPER_SCHEMA_SQL = (
    BASE_SCHEMA_SQL
    + """
CREATE TABLE IF NOT EXISTS biz_paper (
    asset_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '[]',
    pub_year INTEGER,
    venue TEXT NOT NULL DEFAULT '',
    venue_short TEXT NOT NULL DEFAULT '',
    doi TEXT NOT NULL DEFAULT '',
    zotero_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'imported',
    category_id INTEGER,
    url TEXT NOT NULL DEFAULT '',
    pdf_url TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (asset_id) REFERENCES asset_registry(asset_id)
);

CREATE INDEX IF NOT EXISTS idx_biz_paper_status ON biz_paper(status);
CREATE INDEX IF NOT EXISTS idx_biz_paper_category ON biz_paper(category_id);
CREATE INDEX IF NOT EXISTS idx_biz_paper_doi ON biz_paper(doi);
"""
)


# Project P0 当前需要同时查询 Paper 表，因此基于 PAPER_SCHEMA_SQL 扩展。
PROJECT_SCHEMA_SQL = (
    PAPER_SCHEMA_SQL
    + """
CREATE TABLE IF NOT EXISTS biz_project (
    asset_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    project_slug TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    summary TEXT NOT NULL DEFAULT '',
    owner TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES asset_registry(asset_id)
);

CREATE INDEX IF NOT EXISTS idx_biz_project_status ON biz_project(status);
CREATE INDEX IF NOT EXISTS idx_biz_project_slug ON biz_project(project_slug);
"""
)
