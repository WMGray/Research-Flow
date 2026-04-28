---
name: paper-note-generate
description: Maintain Research-Flow's paper `note.md` generation workflow, managed note blocks, figure/table evidence rendering, and tests. Use when changing structured paper summaries, visual evidence in notes, paper note schemas, or deep academic paper reading rules.
---

# Paper Note Generate

## Core Rule

Generate `note.md` from audited canonical sections and figure/table evidence. Do not summarize from the whole raw PDF parse directly, and do not invent unsupported paper facts.

## Workflow

1. Read canonical section files under `parsed/sections/`.
2. Collect image links from section content and resolve them relative to `note.md`.
3. Pass section text plus compact figure/table evidence to the note-generation runtime.
4. Require JSON-only blocks from the LLM.
5. Render managed note blocks deterministically.
6. Always inject available image Markdown into schema-defined note sections: method/problem figures go under `method`, result/appendix figures go under `experimental_results`; do not create a separate top-level visual block.
7. Consume captions and review callouts from `parsed/refined.md` / section files; these should already use Markdown blockquotes (`> **图注**：...`) and `>[!Caution]` callouts before note generation.
8. Preserve user-authored note text by replacing only RF managed blocks.
9. Mark missing or parser-uncertain content explicitly instead of filling gaps.
10. For visual analysis, choose and interpret figures by role, prioritize method figures, and explain what the figure shows, how to read it, and why it matters.

## Note Schema

Managed blocks:

- `paper_overview`: title, authors, year, venue, domain positioning.
- `terminology_guide`: task definitions, model/architecture terms, feature representations, metrics.
- `background_motivation`: research status, related methods, pain-point to contribution mapping.
- `experimental_setup`: datasets, features, training and implementation settings.
- `method`: starts with `### 方法总览`, then gives module-level method explanation, principles, formulas, and effects.
- `experimental_results`: main results, ablations, appendix evidence, table/figure-grounded analysis, and stated limitations/future work as subsections.

## Note Generation Rules

- Use only supplied metadata, canonical sections, and figure/table evidence.
- Top-level note headings must follow the six managed blocks above. Do not add separate top-level `visual_evidence`, `limitations`, or `appendix` sections.
- Renderer-owned block headings must not be repeated inside LLM content; inner headings start at `###`.
- The `method` block must begin with `### 方法总览`; use it to summarize modules, module relationships/data flow, each module's role, and how key method figures support the framework before detailed subsections.
- Preserve technical names in English.
- Keep Table/Figure citations exact and local to the relevant section.
- Do not promote Appendix child headings such as `F.1` into top-level experiment sections.
- If a figure path exists but the caption is missing, state the missing caption rather than guessing.
- Prioritize method figures such as overview, pipeline, framework, architecture, model, module, and workflow figures; use result figures only when they materially support conclusions.
- Explain key figures in Chinese using the three-part logic: what it shows, how to read it, and why it matters.
- Use `>[!Caution]` for caption-missing, unresolved-image, figure/text mismatch, or parser-order uncertainty.
- Generated notes must be detailed deep-reading notes, not short summaries. Follow the runtime contract's minimum length requirements unless supplied section evidence is genuinely missing.
- If evidence is insufficient for a requested subsection, write `Not stated in the parsed paper.`

## Backend Touchpoints

- Note runtime: `backend/core/services/papers/note/runtime.py`
- Paper orchestration: `backend/core/services/papers/repository.py`
- Full-note runtime instructions: `skills/paper-note-generate/references/runtime-instructions.md`
- Per-block runtime instructions: `skills/paper-note-generate/references/block-runtime-instructions.md`
- Tests: `backend/tests/test_paper_refine_runtime.py`, `backend/tests/test_papers_api.py`

## Validation

Run focused checks:

```powershell
python -m pytest tests\test_paper_refine_runtime.py tests\test_papers_api.py -q
```

Review generated `note.md` and confirm that image links are relative to the note file and render in Markdown.
