---
name: paper-refine-parse
description: Maintain Research-Flow's MinerU `full.md` to `parsed/refined.md`, canonical section split, and paper note prompts. Use when changing PDF refine prompts, `skill_bindings.toml`, line-index diagnosis, JSON patch repair, deterministic normalization, heading hierarchy, author metadata cleanup, figure/table text separation, LLM section split plans, verification reports, or tests for academic paper Markdown refinement.
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
11. Route uncertain items to review artifacts; do not silently invent section boundaries.
12. For canonical split, use LLM semantic line-range planning first, after excluding References/Bibliography/Acknowledgments defensively; deterministic heading rules are only a fallback when LLM planning fails or returns unsafe ranges.

## External Patterns

Read `references/paper-reading-patterns.md` before changing prompts for section splitting, figure/table handling, or paper note generation. It records the compact lessons from `claude-scholar` and `AI-paper-reading`: schema-first control, evidence-grounded reading, section-aware ranges, figure/table role awareness, and durable paper-note structure.

## Prompt Rules

- Keep diagnose, repair, and verify prompts separate.
- Require JSON-only responses with `source_hash`.
- Mention the three recurring MinerU failures: ambiguous chapters, figure/text mixing, and reading-order disorder.
- Mention metadata artifacts and heading hierarchy failures explicitly.
- Preserve citations, numbers, formulas, tables, image links, captions, model names, dataset names, and technical terms.
- `parsed/refined.md` must already contain blockquoted figure/table captions (`> **图注**：...`) and human-review callouts (`>[!Caution]`) where captions or image associations are uncertain.
- Preserve author identity exactly; only repair visible spacing/punctuation artifacts.
- Use `mark_needs_review` when the correction requires PDF visual context.
- For split prompts, require line ranges and tell the LLM that child headings such as `5.1` remain under parent `5`.

## Backend Touchpoints

- Runtime: `backend/core/services/papers/refine_runtime.py`
- Prompt/config helper: `backend/core/services/papers/prompt_runtime.py`
- Deterministic normalization: `backend/core/services/papers/refine_normalization.py`
- Canonical split runtime: `backend/core/services/papers/section_split_runtime.py`
- Refine contracts and parsing helpers: `backend/core/services/papers/refine_parsing.py`
- Patch and verification helpers: `backend/core/services/papers/refine_patch.py`
- Binding config: `backend/config/skill_bindings.toml`
- Prompt registry: `backend/config/prompt_templates.toml`
- Merged refine prompt file: `backend/config/prompts/paper_refine.md`
- Section split prompt: `backend/config/prompts/paper_section_split.md`
- Note generation skill: `skills/paper-note-generate/SKILL.md`
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
- `parsed/sections/split_report.json`: split strategy, LLM usage, accepted/rejected line ranges.

## Reference

Read `references/patch-contract.md` before changing patch schemas or prompt JSON examples.
Read `references/paper-reading-patterns.md` before changing refine/split/note prompt strategy.
