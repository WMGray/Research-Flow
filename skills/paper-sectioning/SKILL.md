---
name: paper-sectioning
description: Maintain Research-Flow's paper sectioning skill for splitting `parsed/refined.md` into six canonical Markdown files using audited semantic line ranges. Use when changing section keys, LLM classification rules, multi-section matching, reference exclusion, split validation, or `paper_sectioning.default` runtime instructions.
---

# Paper Sectioning

## Boundary

This skill plans semantic line ranges from `parsed/refined.md`. It does not rewrite, summarize, or improve paper content. The backend copies accepted lines into canonical section files, writes placeholders for missing sections, and provides deterministic fallback.

## Output Files

The backend always writes these files under `parsed/sections/`:

- `01_introduction.md`: title, authors, abstract, problem definition, motivation, and contributions.
- `02_related_work.md`: literature discussion, including prior-work content embedded in Introduction, body sections, or Appendix.
- `03_method.md`: method, model, algorithm, architecture, system design, theory, and proofs; appendix lines may also appear here when they are method evidence.
- `04_experiment.md`: experiments, results, ablations, analysis, implementation details, metrics, baselines, and dataset descriptions; appendix lines may also appear here when they are experiment evidence.
- `05_conclusion.md`: conclusion, limitations, and future work.
- `06_appendix.md`: complete appendix or supplementary content in original order.

Together, the files should cover the whole paper document except References/Bibliography and parser metadata. Do not drop headings, paragraphs, equations, tables, figures, or captions just because their semantic class is ambiguous.

## LLM Contract

The LLM returns JSON with `sections[]`; each item is an audited line range:

- `section_key`: one of `introduction`, `related_work`, `method`, `experiment`, `conclusion`, `appendix`.
- `start_line` / `end_line`: 1-based inclusive line numbers in `refined.md`.
- `confidence`: use `< 0.65` only for ranges the backend should reject.
- `rationale`: brief evidence for the semantic choice.

Every non-reference line in `refined.md` should appear in at least one returned range. Figures, tables, image Markdown, captions, and review callouts move with the surrounding semantic block.

The backend accepts overlapping ranges for intended duplication. Use overlap only when the same paragraph, heading, figure, or table genuinely belongs in more than one output file:

- `introduction` + `related_work` for literature discussion embedded in Introduction.
- `appendix` + `method` for appendix proofs or method details.
- `appendix` + `experiment` for appendix experiments, ablations, datasets, or result analysis.
- `appendix` + `related_work` for appendix literature discussion.
- Other section combinations are also valid when a single line range has multiple clear semantic roles.

## Classification Rules

- Use semantic role, not exact heading text.
- `introduction`: title/front matter, abstract, research problem, motivation, contributions, and paper organization.
- `related_work`: concrete prior work, citations used for literature comparison, limitations of existing methods, and research gap discussion.
- `method`: proposed approach, algorithm steps, model architecture, objective functions, training/inference design, theoretical derivation, and proofs.
- `experiment`: datasets, metrics, implementation settings, baselines, quantitative/qualitative results, ablations, sensitivity analysis, and discussion of empirical findings.
- `conclusion`: closing summary, limitations, future work, and final implications.
- `appendix`: every appendix/supplementary line. If an appendix subsection also provides method, experiment, or related-work evidence, it may also be emitted with the matching non-appendix `section_key`.

## Multi-Section Matching

- A line range can be selected for multiple sections when it has multiple semantic roles.
- Use multi-section matching sparingly; do not duplicate content just because it is in Appendix.
- Keep `06_appendix.md` complete when appendix content exists; any additional non-appendix range is a semantic copy, not a move.

## Exclusion Rules

Do not select References, Bibliography, parser metadata, page headers/footers, or unrelated boilerplate. The backend also removes these defensively from accepted ranges and fills uncovered non-reference paper lines with deterministic assignments.

## Runtime Reference

Runtime instructions live in `references/runtime-instructions.md`. Keep the JSON schema aligned with `backend/core/services/papers/split/runtime.py`.

## Validation

Run focused tests after changes:

```powershell
python -m pytest backend\tests\test_paper_refine_runtime.py backend\tests\test_papers_api.py -q
```
