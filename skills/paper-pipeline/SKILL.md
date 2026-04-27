---
name: paper-pipeline
description: Maintain Research-Flow's end-to-end Paper workflow. Use when changing Paper download, MinerU raw Markdown parsing, refine-parse, section splitting, note generation with figure/table evidence, Paper artifacts, pipeline runs, API contracts, or focused tests.
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
6. Generate `note.md` only from semantic section files; split must remove References/Acknowledgments, preserve Appendix, keep figures/captions, and use LLM line-range plans as audited control data.
7. If LLM split fails or returns unsafe ranges, fall back to deterministic split; reject low-confidence, overlapping, unknown section keys, or ranges that only contain excluded non-paper content.
8. Preserve user-authored note text. Only update RF managed blocks when regenerating notes.

## Code Touchpoints

- API: `backend/app/api/papers.py`
- API schemas: `backend/app/schemas/papers.py`
- Core DTOs: `backend/core/services/papers/models.py`
- Orchestration: `backend/core/services/papers/service.py`
- Persistence and artifacts: `backend/core/services/papers/repository.py`
- Skill runtime helper: `backend/core/services/papers/skill_runtime.py`
- Refine runtime: `backend/core/services/papers/refine/runtime.py`
- Refine normalization: `backend/core/services/papers/refine/normalization.py`
- Section split runtime: `backend/core/services/papers/split/runtime.py`
- Note runtime: `backend/core/services/papers/note/runtime.py`
- Paper skills: `skills/paper-refine-parse/`, `skills/paper-sectioning/`, `skills/paper-note-generate/`, `skills/paper-knowledge-mining/`, `skills/paper-dataset-mining/`
- Schema: `backend/core/schema.py`
- Runtime LLM instructions: `skills/{paper-skill}/references/runtime-instructions.md`
- Tests: `backend/tests/test_papers_api.py`, `backend/tests/test_paper_refine_runtime.py`

## LLM Output Contract

- Refine calls must return JSON-only control data and preserve citations, formulas, numbers, image links, captions, datasets, model names, and technical terms.
- Section split calls must return JSON-only semantic line ranges, merge Introduction/Related Work into the background file when appropriate, include Appendix, and treat child headings like `5.1` as children of parent `5`.
- Summary calls must return JSON blocks, use only supplied section text and figure/table evidence, and treat `Pending extraction` as missing evidence.
- Generated `note.md` must embed available figures/tables with paths relative to `note.md`; the LLM explains images but code renders image Markdown.
- Keep model-facing skill instructions separate from backend rendering logic.

## Validation

Run focused checks after changes:

```powershell
python -m compileall core\services\papers app\api\papers.py app\schemas\papers.py tests\test_papers_api.py
python -m ruff check core\services\papers app\api\papers.py app\schemas\papers.py tests\test_papers_api.py
```

If pytest temp directories are inaccessible on Windows, use a clean accessible `--basetemp` or a TestClient smoke script. Do not reuse known blocked pytest temp directories.
