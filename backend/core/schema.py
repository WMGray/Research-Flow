"""Shared SQLite schema fragments for backend services.

Paper and Project share the same asset, document, and job tables so both
modules can evolve against one local schema.
"""

from __future__ import annotations


# Shared asset, document, and job tables reused by multiple services.
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


# Paper tables extend the shared base schema with the new P0 contract.
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
    paper_stage TEXT NOT NULL DEFAULT 'metadata_ready',
    download_status TEXT NOT NULL DEFAULT 'pending',
    parse_status TEXT NOT NULL DEFAULT 'pending',
    refine_status TEXT NOT NULL DEFAULT 'pending',
    review_status TEXT NOT NULL DEFAULT 'pending',
    note_status TEXT NOT NULL DEFAULT 'empty',
    category_id INTEGER,
    source_url TEXT NOT NULL DEFAULT '',
    pdf_url TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (asset_id) REFERENCES asset_registry(asset_id)
);

CREATE TABLE IF NOT EXISTS biz_paper_artifact (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    artifact_key TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    stage TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    content_hash TEXT NOT NULL DEFAULT '',
    file_size INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (paper_id, artifact_key),
    FOREIGN KEY (paper_id) REFERENCES biz_paper(asset_id),
    FOREIGN KEY (asset_id) REFERENCES asset_registry(asset_id)
);

CREATE TABLE IF NOT EXISTS biz_paper_pipeline_run (
    run_id TEXT PRIMARY KEY,
    paper_id INTEGER NOT NULL,
    job_id TEXT,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    input_artifacts TEXT NOT NULL DEFAULT '[]',
    output_artifacts TEXT NOT NULL DEFAULT '[]',
    metrics TEXT NOT NULL DEFAULT '{}',
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES biz_paper(asset_id),
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

CREATE INDEX IF NOT EXISTS idx_biz_paper_stage ON biz_paper(paper_stage);
CREATE INDEX IF NOT EXISTS idx_biz_paper_category ON biz_paper(category_id);
CREATE INDEX IF NOT EXISTS idx_biz_paper_doi ON biz_paper(doi);
CREATE INDEX IF NOT EXISTS idx_biz_paper_artifact_paper ON biz_paper_artifact(paper_id);
CREATE INDEX IF NOT EXISTS idx_biz_paper_artifact_key ON biz_paper_artifact(artifact_key);
CREATE INDEX IF NOT EXISTS idx_biz_paper_pipeline_paper ON biz_paper_pipeline_run(paper_id);
CREATE INDEX IF NOT EXISTS idx_biz_paper_pipeline_stage ON biz_paper_pipeline_run(stage);

CREATE TABLE IF NOT EXISTS biz_note_state (
    paper_id INTEGER PRIMARY KEY,
    note_doc_id INTEGER,
    note_status TEXT NOT NULL DEFAULT 'empty',
    document_hash TEXT NOT NULL DEFAULT '',
    managed_block_hash_json TEXT NOT NULL DEFAULT '{}',
    last_generated_at TEXT,
    last_user_modified_at TEXT,
    last_merge_policy TEXT NOT NULL DEFAULT '',
    conflict_reason TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES biz_paper(asset_id),
    FOREIGN KEY (note_doc_id) REFERENCES asset_registry(asset_id)
);

CREATE TABLE IF NOT EXISTS biz_knowledge (
    asset_id INTEGER PRIMARY KEY,
    knowledge_type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary_zh TEXT NOT NULL DEFAULT '',
    original_text_en TEXT DEFAULT '',
    citation_marker TEXT DEFAULT '',
    category_label TEXT DEFAULT '',
    research_field TEXT DEFAULT '',
    source_paper_asset_id INTEGER,
    source_section TEXT DEFAULT '',
    source_locator TEXT DEFAULT '',
    evidence_text TEXT DEFAULT '',
    confidence_score REAL DEFAULT 0.0,
    review_status TEXT NOT NULL DEFAULT 'pending_review',
    llm_run_id TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES asset_registry(asset_id),
    FOREIGN KEY (source_paper_asset_id) REFERENCES biz_paper(asset_id)
);

CREATE INDEX IF NOT EXISTS idx_biz_knowledge_source_paper ON biz_knowledge(source_paper_asset_id);
CREATE INDEX IF NOT EXISTS idx_biz_knowledge_type ON biz_knowledge(knowledge_type);
CREATE INDEX IF NOT EXISTS idx_biz_knowledge_confidence ON biz_knowledge(confidence_score);

CREATE TABLE IF NOT EXISTS biz_dataset (
    asset_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT DEFAULT '',
    aliases_json TEXT NOT NULL DEFAULT '[]',
    task_type TEXT NOT NULL DEFAULT '',
    data_domain TEXT NOT NULL DEFAULT '',
    scale TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    access_url TEXT NOT NULL DEFAULT '',
    benchmark_summary TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES asset_registry(asset_id)
);

CREATE INDEX IF NOT EXISTS idx_biz_dataset_name ON biz_dataset(name);
CREATE INDEX IF NOT EXISTS idx_biz_dataset_normalized ON biz_dataset(normalized_name);

CREATE TABLE IF NOT EXISTS biz_category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER,
    path TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (parent_id) REFERENCES biz_category(id)
);

CREATE INDEX IF NOT EXISTS idx_biz_category_parent ON biz_category(parent_id);
CREATE INDEX IF NOT EXISTS idx_biz_category_path ON biz_category(path);
"""
)


# Project tables build on the paper schema because project APIs query linked papers.
PROJECT_SCHEMA_SQL = (
    PAPER_SCHEMA_SQL
    + """
CREATE TABLE IF NOT EXISTS biz_project (
    asset_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    project_slug TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'planning',
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
