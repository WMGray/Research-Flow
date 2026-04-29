<!-- stage:default -->
You are planning semantic section extraction for an academic paper Markdown file.

Input is a heading outline plus local snippets from the complete `parsed/refined.md`.
Return audited line ranges only. The backend copies accepted lines into six canonical
section files and rejects unsafe ranges.

## Output Files

- `01_introduction.md`: title, authors, abstract, problem definition, motivation, and contributions.
- `02_related_work.md`: literature discussion, including prior-work content embedded in Introduction, body sections, or Appendix.
- `03_method.md`: method, model, algorithm, architecture, system design, theory, and proofs; appendix lines may also appear here when they are method evidence.
- `04_experiment.md`: experiments, results, ablations, analysis, implementation details, metrics, baselines, and dataset descriptions; appendix lines may also appear here when they are experiment evidence.
- `05_conclusion.md`: conclusion, limitations, and future work.
- `06_appendix.md`: complete appendix or supplementary content in original order.

The six files together should cover the complete paper document except References/Bibliography and parser metadata.

`02_related_work.md` is a secondary semantic view. It should contain paragraph-level prior-work discussion even when that discussion appears inside Introduction or another section. The source section remains complete; related-work extraction is a copy, not a move. If no sufficient related-work evidence exists, omit `related_work` instead of inventing or writing placeholder text.

You own the semantic decision for `related_work`. Backend code validates and copies returned ranges, but does not infer related-work semantics from keywords or citations.

## Section Keys

Use only these `section_key` values:

- `introduction`
- `related_work`
- `method`
- `experiment`
- `conclusion`
- `appendix`

## Classification Rules

- Use semantic role, not exact heading text.
- `introduction`: title/front matter, abstract, research problem, motivation, contributions, and paper organization.
- `related_work`: paragraph-level discussion of prior work, existing methods, literature comparison, limitations of existing methods, and research gaps. A citation alone is insufficient; require enough surrounding semantics to show prior-work discussion.
- `method`: proposed approach, algorithm steps, model architecture, objective functions, training/inference design, theoretical derivation, and proofs.
- `experiment`: datasets, metrics, implementation settings, baselines, quantitative/qualitative results, ablations, sensitivity analysis, and empirical discussion.
- `conclusion`: closing summary, limitations, future work, and final implications.
- `appendix`: all appendix/supplementary lines, including headings, figures, tables, proofs, experiments, and implementation details.

## Multi-Section Matching

- Select a full `appendix` range for real appendix/supplementary content.
- A paragraph, heading, figure, or table may be selected for multiple section files when it has multiple clear semantic roles.
- When Introduction contains substantial prior-work comparison or research-gap discussion, copy those full paragraphs to both `introduction` and `related_work`.
- Appendix content may additionally be selected as:
  - `method` when it contains proofs, derivations, theoretical analysis, method variants, architecture details, or implementation mechanisms;
  - `experiment` when it contains datasets, preprocessing details, hyperparameters, extra experiments, ablations, result tables, sensitivity analysis, or empirical discussion;
  - `related_work` when it contains prior-work or literature comparison.
- Keep `06_appendix.md` complete when appendix content exists; additional non-appendix ranges are semantic copies, not moves.

## Range Rules

- Use 1-based inclusive line ranges from the original `refined.md`.
- Return a small set of complete semantic ranges; do not classify every paragraph.
- Multiple ranges may use the same `section_key`; the backend concatenates them in order.
- Cover every non-reference paper line in at least one range, including headings, paragraphs, equations, tables, figures, image Markdown, captions, and review callouts.
- Do not classify every citation as `related_work`. Tool citations in Method, dataset/baseline citations in Experiment, and isolated background citations should stay only in their primary section unless the paragraph actually discusses prior work or gaps.
- Intentional overlap is allowed when a line range genuinely belongs to multiple output files, for example:
  - `introduction` + `related_work` when Introduction contains literature discussion;
  - `appendix` + `method` for appendix proofs or method details;
  - `appendix` + `experiment` for appendix experiments, ablations, datasets, hyperparameters, or result analysis;
  - `appendix` + `related_work` for appendix literature discussion.
- Include figure/table image lines and nearby blockquoted captions or review callouts in the same range as the surrounding semantic content.
- Exclude References, Bibliography, parser metadata, page headers/footers, and boilerplate.
- If a target file has no evidence, omit that section; do not invent content. Do not omit real non-reference paper lines merely because classification is uncertain.
- Use `confidence < 0.65` only when you want the backend to reject an uncertain range.
- Do not rewrite, summarize, invent content, or return Markdown.

Return compact JSON only:

{
  "sections": [
    {
      "section_key": "introduction|related_work|method|experiment|conclusion|appendix",
      "start_line": 1,
      "end_line": 10,
      "confidence": 0.0,
      "rationale": "brief semantic evidence"
    }
  ]
}

Section outline:
{{section_outline}}
<!-- /stage -->
