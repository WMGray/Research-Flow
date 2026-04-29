---
name: paper-refine-parse
description: This skill should be used when the user asks to "refine paper parse", "fix MinerU output", "repair full.md", "run paper refinement", "diagnose parse issues", "verify refined paper", "fix formula delimiters", "normalize paper headings", or needs to maintain the MinerU full.md to parsed/refined.md pipeline.
---

# Paper Refine Parse

## Goal

Produce `parsed/refined.md` from MinerU `full.md` via LLM-diagnosed local patches plus deterministic normalization.

## Core Rule

Treat MinerU `full.md` as the source artifact and LLM output as structured control data. The backend must build `parsed/refined.md` by applying verified local patches plus deterministic normalization.

## Boundary

This skill diagnoses and repairs visible MinerU parse artifacts. It does not rewrite, summarize, translate, or improve paper content. It must never invent metadata, affiliations, references, author identities, or paper facts. When a correction requires unavailable source context, it routes the item to review artifacts instead of guessing.

## Verification Philosophy

Verification is an annotation step for human follow-up, not a gatekeeper. The pipeline favors generating output with review flags over blocking on surface-level issues. Reserve `fail` only for unambiguous content destruction; most refinement issues should carry `warning` so the file is written, the pipeline continues, and a human corrects the remaining annotations later.

## Workflow

1. Read `parsed/raw.md` or the test fixture representing MinerU `full.md`.
2. Build `parsed/refine/line_index.json` with stable line numbers and source hash.
3. Build compact structural evidence windows from the full line index.
4. Run `paper_refine_parse.diagnose` to produce issue JSON.
5. Run `paper_refine_parse.repair` to produce line-based patch JSON.
6. Apply patches in code, reject low-confidence, overlapping, out-of-range, or empty replacements.
7. Apply deterministic normalization after patching (heading hierarchy, front matter, figure/table blocks, callouts, formula wrappers).
8. Let LLM repair patches normalize visible formula wrappers (see `references/patch-contract.md` for formula repair rules).
9. Run local preservation checks plus `paper_refine_parse.verify` when LLM patches changed text.
10. Write `parsed/refined.md`. When verification returns `warning`, the file is written with inline review annotations for human follow-up. Only when verification returns `fail` (unambiguous content destruction) does the pipeline mark the job as failed while still writing an annotated candidate file.
11. If LLM control JSON is invalid, do not apply unsafe LLM patches; deterministic normalization may still make safe structural changes and must be recorded in `deterministic_normalization.json`.
12. Route uncertain items to review artifacts; do not silently invent paper structure.

## LLM Output Contract

The LLM must return JSON-only responses with `source_hash` across three separate stages: diagnose, repair, and verify. See `references/patch-contract.md` for complete JSON schemas.

Key constraints:
- Mention only visible MinerU failures: metadata layout, heading hierarchy, float placement, captions, formula delimiters, reading order, or OCR artifacts.
- Preserve citations, numbers, formulas, tables, image links, captions, model names, dataset names, and technical terms.
- Formula delimiter repair only wraps visible formula payloads. It may remove MinerU wrapper tokens but must not rewrite symbols, numbers, operators, spacing, subscripts, or superscripts.
- Use `mark_needs_review` when the correction requires unavailable source context.

## Backend Touchpoints

- Runtime: `backend/core/services/papers/refine/runtime.py`
- Skill runtime helper: `backend/core/services/papers/skill_runtime.py`
- Deterministic normalization: `backend/core/services/papers/refine/normalization.py`
- Refine contracts and parsing helpers: `backend/core/services/papers/refine/parsing.py`
- Patch and verification helpers: `backend/core/services/papers/refine/patch.py`
- Runtime refine instructions: `skills/paper-refine-parse/references/runtime-instructions.md`
- Tests: `backend/tests/test_paper_refine_runtime.py`, `backend/tests/test_papers_api.py`

## Validation

Run focused tests after changes:

```powershell
python -m pytest backend\tests\test_paper_refine_runtime.py backend\tests\test_papers_api.py -q
```

If pytest temp directories are inaccessible on Windows, use a clean accessible `--basetemp` outside the blocked directories and do not delete unrelated temp folders.

Review outputs before accepting a change:

- `parsed/refine/deterministic_normalization.json`: operation count and exact before/after lines.
- `parsed/refine/verify.json`: local preservation status.

## References

- `references/runtime-instructions.md` — LLM prompt templates for diagnose, repair, verify, and default stages
- `references/patch-contract.md` — JSON schemas for diagnosis, patch, verification, and deterministic normalization artifacts; formula repair rules
