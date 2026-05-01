---
name: paper-note-generate
description: "Generate structured Chinese paper deep-reading notes (note.md) from paper-sectioning canonical sections, metadata, and figure/table evidence. Use when Codex needs to generate note.md, improve note generation rules, revise managed note blocks, tune figure evidence handling, or update the paper-style reading architecture: 摘要信息, 术语, 背景动机, 方法, 实验/结果, 结论局限."
---

# Paper Note Generate

## Goal

Generate `note.md` from paper metadata, six canonical section files, and figure/table evidence. The output is a Chinese deep-reading note organized like a paper walkthrough:

```
摘要信息 -> 术语 -> 背景动机 -> 方法 -> 实验/结果 -> 结论局限
```

Use this structure to explain the paper progressively: identify the paper and abstract first, define terms before they are used, explain the research gap, unpack the method, verify it through experiments/results, then close with conclusions and limitations.

## Skill Design

Follow the official skill shape:

- Keep `SKILL.md` concise: routing, workflow, block contract, and reference map only.
- Put long prompt text, quality rules, section budgets, method rules, and figure rules in `references/`.
- Load references only when needed for the current edit or generation path.
- Keep frontmatter limited to `name` and `description`; all trigger context belongs in `description`.

## Boundary

This skill uses only supplied metadata, `paper-sectioning` outputs, and figure/table evidence. Do not invent paper facts, authors, venues, datasets, metrics, numbers, or conclusions. When evidence is insufficient, write the gap explicitly instead of guessing.

## Pipeline Position

```
refine-parse -> sectioning --> note-generate --> knowledge-mining
                            \-> dataset-mining (parallel with note)
```

`note.md` is consumed by `paper-knowledge-mining` through `{{note_context}}`. `paper-dataset-mining` shares the same sectioning input but does not depend on `note.md`.

## Managed Blocks

| Order | Block ID | Title | Primary Evidence |
|-------|----------|-------|------------------|
| 1 | `paper_overview` | 摘要信息 | metadata, abstract, introduction |
| 2 | `terminology_guide` | 术语 | introduction, related work, method, experiment |
| 3 | `background_motivation` | 背景动机 | introduction, related work |
| 4 | `method` | 方法 | method, appendix method/proofs |
| 5 | `experimental_results` | 实验/结果 | experiment, appendix experiments |
| 6 | `conclusion_limitations` | 结论局限 | conclusion, discussion, limitations, future work |

Do not create extra top-level note blocks. Appendix, supplementary experiments, proofs, implementation details, discussion, limitations, and future work must be routed into the six blocks above.

## Workflow

1. Read the six canonical section files under `parsed/sections/`.
2. Collect image links from section content. The backend resolves paths relative to `note.md`, classifies each figure role, and creates compact `Figure/Table Evidence`.
3. Build either the full-note prompt from `references/runtime-instructions.md` or per-block prompt from `references/block-runtime-instructions.md`.
4. Require the LLM to return JSON only. Full-note mode returns `{"blocks": {...}}`; block mode returns `{"content": "..."}`.
5. Let the LLM place `<!-- figure -->` markers where figures should appear. The backend replaces markers with rendered Markdown and appends unused figures at block end.
6. Render managed blocks into `note.md` while preserving user-authored content outside managed blocks.

## Progressive Disclosure Map

Load only the file needed for the task:

- `references/runtime-instructions.md` — full-note LLM prompt template and the six-block paper walkthrough.
- `references/block-runtime-instructions.md` — per-block LLM prompt template.
- `references/section-scope.md` — section selection, per-block evidence routing, and context budgets.
- `references/method-block-spec.md` — method block hierarchy, formula rules, and figure analysis rules.
- `references/figure-handling.md` — figure collection, role classification, and inline embedding conventions.
- `references/quality-standards.md` — minimum content, required items, and forbidden patterns.

## Backend Touchpoints

- `backend/core/services/papers/note/schema.py` — block definitions, order, section keys, and per-block instructions.
- `backend/core/services/papers/note/context.py` — per-block context compaction.
- `backend/core/services/papers/note/visuals.py` — figure collection, role classification, and inline embedding.
- `backend/core/services/papers/note/blocks.py` — block assembly, fallback text, and finalization.
- `backend/core/services/papers/repository.py` — pipeline integration through `run_generate_note`.

## Validation

Run focused tests after note-generation changes:

```powershell
python -m pytest backend\tests\test_paper_refine_runtime.py backend\tests\test_papers_api.py -q
```

Review generated `note.md` manually when prompt behavior changes. Confirm the six headings, evidence grounding, relative image links, inline figures, and preserved user-authored content.
