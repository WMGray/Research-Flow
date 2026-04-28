---
name: paper-refine-parse
description: Maintain Research-Flow's MinerU `full.md` to `parsed/refined.md` refinement workflow, including local patch repair, deterministic normalization, verification, and related tests.
---

# Paper Refine Parse

## Core Rule

Treat MinerU `full.md` as the source artifact and LLM output as structured control data. The backend must build `parsed/refined.md` by applying verified local patches plus deterministic normalization.

## Workflow

1. Read `parsed/raw.md` or the test fixture representing MinerU `full.md`.
2. Build `parsed/refine/line_index.json` with stable line numbers and source hash.
3. Build compact structural evidence windows from the full line index.
4. Run `paper_refine_parse.diagnose` to produce issue JSON.
5. Run `paper_refine_parse.repair` to produce line-based patch JSON.
6. Apply patches in code, reject low-confidence, overlapping, out-of-range, or empty replacements.
7. Apply deterministic normalization after patching:
   - normalize numbered heading hierarchy (`5` -> major, `5.1` -> child);
   - normalize visible front matter to `Authors: ...` and `Institutions: ...`;
   - keep figure/table blocks at paragraph boundaries with `> Figure ...` / `> Table ...` captions;
   - convert unresolved caption-review callouts to `>[!warning]`;
   - convert MinerU formula wrappers such as `equation_inline ... text` to Markdown math;
   - preserve citations, numbers, formulas, image links, tables, and captions.
8. Let LLM repair patches normalize visible formula wrappers:
   - wrap bare TeX fragments with `$...$` or `$$...$$`;
   - convert MinerU placeholders such as `equation_inline \Delta W _ { q } text` to `$\Delta W _ { q }$`.
9. Run local preservation checks plus `paper_refine_parse.verify` when LLM patches changed text.
10. Write `parsed/refined.md` only when verification does not fail.
11. If LLM control JSON is invalid, do not apply unsafe LLM patches; deterministic normalization may still make safe structural changes and must be recorded in `deterministic_normalization.json`.
12. Route uncertain items to review artifacts; do not silently invent paper structure.

## LLM Output Contract

- Keep diagnose, repair, and verify stages separate.
- Require JSON-only responses with `source_hash`.
- Mention only visible MinerU failures: metadata layout, heading hierarchy, float placement, captions, formula delimiters, reading order, or OCR artifacts.
- Preserve citations, numbers, formulas, tables, image links, captions, model names, dataset names, and technical terms.
- `parsed/refined.md` uses `Authors: ...`, `Institutions: ...`, `> Figure ...`, `> Table ...`, and `>[!warning]`.
- Formula delimiter repair only wraps visible formula payloads. It may remove MinerU wrapper tokens `equation_inline` and `text`, but must not rewrite symbols, numbers, operators, spacing, subscripts, or superscripts.
- Do not leave partial repairs such as `$A$ text`, `$B$ text`, or any `equation_inline ... text` shell in accepted replacements.
- Preserve author identity and reference order; do not invent affiliations, references, or paper content.
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
python -m pytest tests\test_paper_refine_runtime.py tests\test_papers_api.py -q
```

If pytest temp directories are inaccessible on Windows, use a clean accessible `--basetemp` outside the blocked directories and do not delete unrelated temp folders.

Review outputs before accepting a change:

- `parsed/refine/deterministic_normalization.json`: operation count and exact before/after lines.
- `parsed/refine/verify.json`: local preservation status.

## Reference

Read `references/patch-contract.md` before changing patch schemas or JSON examples.
