---
name: paper-refine-parse
description: Maintain Research-Flow's MinerU `full.md` to `parsed/refined.md` workflow. Use when changing line-index diagnosis, JSON patch repair, deterministic normalization, heading hierarchy, author metadata cleanup, figure/table text separation, verification reports, or tests for academic paper Markdown refinement.
---

# Paper Refine Parse

## Core Rule

Treat MinerU `full.md` as the source artifact and LLM output as structured control data. Do not ask the LLM to rewrite the whole paper. The backend must build `parsed/refined.md` by applying verified local patches plus deterministic normalization.

## Workflow

1. Read `parsed/raw.md` or the test fixture representing MinerU `full.md`.
2. Build `parsed/refine/line_index.json` with stable line numbers and source hash.
3. Build compact structural evidence windows from the full line index; do not send the whole paper to the LLM by default.
4. Run `paper_refine_parse.diagnose` to produce issue JSON.
5. Run `paper_refine_parse.repair` to produce line-based patch JSON.
6. Apply patches in code, reject low-confidence, overlapping, out-of-range, or empty replacements.
7. Apply deterministic normalization after patching:
   - normalize numbered heading hierarchy (`5` -> major, `5.1` -> child);
   - repair safe title/author metadata spacing artifacts in the early metadata window;
   - render figure/table captions as Markdown blockquotes and mark missing captions with `>[!Caution]`;
   - preserve citations, numbers, formulas, image links, tables, and captions.
8. Run local preservation checks plus `paper_refine_parse.verify` when LLM patches changed text.
9. Write `parsed/refined.md` only when verification does not fail.
10. If LLM control JSON is invalid, do not apply unsafe LLM patches; deterministic normalization may still make safe structural changes and must be recorded in `deterministic_normalization.json`.
11. Route uncertain items to review artifacts; do not silently invent paper structure.

## LLM Output Contract

- Keep diagnose, repair, and verify stages separate.
- Require JSON-only responses with `source_hash`.
- Mention the three recurring MinerU failures: ambiguous chapters, figure/text mixing, and reading-order disorder.
- Mention metadata artifacts and heading hierarchy failures explicitly.
- Preserve citations, numbers, formulas, tables, image links, captions, model names, dataset names, and technical terms.
- `parsed/refined.md` must already contain blockquoted figure/table captions (`> **图注**：...`) and human-review callouts (`>[!Caution]`) where captions or image associations are uncertain.
- Preserve author identity exactly; only repair visible spacing/punctuation artifacts.
- Use `mark_needs_review` when the correction requires PDF visual context.

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
python -m pytest tests\test_paper_refine_runtime.py tests\test_papers_api.py -q
```

If pytest temp directories are inaccessible on Windows, use a clean accessible `--basetemp` outside the blocked directories and do not delete unrelated temp folders.

Review outputs before accepting a change:

- `parsed/refine/deterministic_normalization.json`: operation count and exact before/after lines.
- `parsed/refine/verify.json`: local preservation status.

## Reference

Read `references/patch-contract.md` before changing patch schemas or JSON examples.
