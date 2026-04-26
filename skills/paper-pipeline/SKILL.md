---
name: paper-pipeline
description: Maintain Research-Flow's end-to-end Paper workflow. Use when changing Paper download, MinerU raw Markdown parsing, refine-parse, section splitting, note generation, Paper artifacts, pipeline runs, prompts, API contracts, or focused tests.
---

# Paper Pipeline

## Core Contract

Paper processing is an auditable chain:

```text
create/import -> download -> parse raw.md -> refine -> split -> summarize -> extract
```

Keep `biz_paper` focused on status and metadata. Store files in the filesystem, register machine outputs in `biz_paper_artifact`, and record each stage in `biz_paper_pipeline_run`.

## Workflow Rules

1. Preserve the stage order unless the request explicitly targets one stage.
2. Treat MinerU `full.md` / `parsed/raw.md` as the parse source artifact.
3. Do not ask an LLM to rewrite a full paper freely; refine must use diagnose / repair patch / deterministic normalization / verify.
4. Write every durable machine output as an artifact with a stable `artifact_key`.
5. Record each action as a job and pipeline run, including failed precondition jobs.
6. Generate `note.md` only from canonical sections; split must respect heading hierarchy and may use LLM line-range plans only as audited control data.
7. If deterministic split misses major sections, use the section split prompt to recover canonical line ranges; reject low-confidence, overlapping, or unknown section keys.
8. Preserve user-authored note text. Only update RF managed blocks when regenerating notes.

## Code Touchpoints

- API: `backend/app/api/papers.py`
- API schemas: `backend/app/schemas/papers.py`
- Core DTOs: `backend/core/services/papers/models.py`
- Orchestration: `backend/core/services/papers/service.py`
- Persistence and artifacts: `backend/core/services/papers/repository.py`
- Prompt/config helper: `backend/core/services/papers/prompt_runtime.py`
- Refine runtime: `backend/core/services/papers/refine_runtime.py`
- Refine normalization: `backend/core/services/papers/refine_normalization.py`
- Section split runtime: `backend/core/services/papers/section_split_runtime.py`
- Note runtime: `backend/core/services/papers/summary_runtime.py`
- Schema: `backend/core/schema.py`
- Prompts: `backend/config/prompts/`, `backend/config/prompt_templates.toml`
- Tests: `backend/tests/test_papers_api.py`, `backend/tests/test_paper_refine_runtime.py`

## Prompt Rules

- Refine prompts must return JSON-only control data and preserve citations, formulas, numbers, image links, captions, datasets, model names, and technical terms.
- Section split prompts must return JSON-only canonical line ranges and treat child headings like `5.1` as children of parent `5`.
- Summary prompts must return JSON blocks, use only supplied section text, and treat `Pending extraction` as missing evidence.
- Keep model-facing prompts separate from backend rendering logic.

## Validation

Run focused checks after changes:

```powershell
python -m compileall core\services\papers app\api\papers.py app\schemas\papers.py tests\test_papers_api.py
python -m ruff check core\services\papers app\api\papers.py app\schemas\papers.py tests\test_papers_api.py
```

If pytest temp directories are inaccessible on Windows, use a clean accessible `--basetemp` or a TestClient smoke script. Do not reuse known blocked pytest temp directories.
