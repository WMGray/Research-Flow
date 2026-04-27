You are planning semantic section extraction for an academic paper Markdown file.

You receive heading evidence and local snippets from the complete `parsed/refined.md`.
Do not rewrite or summarize the paper. Return only audited line ranges. The backend
will copy the selected Markdown lines into section files, preserving equations,
tables, images, blockquoted captions, and caution callouts.

Target output files:
- `related_work.md`: research background, motivation, Introduction, problem setting, and Related Work. Merge Introduction and Related Work here when both exist; the file name is canonical, not a strict title match.
- `method.md`: main approach, model, algorithm, architecture, system, theoretical method, and method-specific figures.
- `experiment.md`: datasets, metrics, baselines, implementation details, experiments, evaluation, results, ablations, and analysis.
- `appendix.md`: appendices, supplementary material, additional experiments, extra proofs, extra implementation details, and appendix figures/tables.
- `conclusion.md`: conclusion, limitations, discussion, and future work.

Rules:
- Use full line ranges from refined.md, inclusive.
- Split by semantic content, not by keyword matching. A section heading does not need to literally match the target file name if its content belongs there.
- It is valid to return multiple ranges with the same `section_key`; the backend will concatenate them in order. Use this to merge Introduction and Related Work into `related_work`.
- Treat numbered child headings like `5.1`, `5.2`, `A.1` as children of their nearest parent unless the outline clearly shows a new top-level section.
- If MinerU made parent and child headings the same Markdown level, trust numbering hierarchy and local snippets over Markdown level.
- Exclude References, Bibliography, Acknowledgments, author affiliations, metadata, parser metadata, and unrelated boilerplate. The backend also removes these lines defensively.
- Do not exclude Appendix; Appendix is paper content and must be returned under `appendix` when present, even if it appears after References.
- Preserve figure lines and their following `> **图注**：...` or `>[!Caution]` lines by selecting ranges that include them.
- If evidence is insufficient for a target file, omit that section instead of guessing.
- Use confidence below 0.65 for uncertain ranges so the backend rejects them.
- Do not split the paper into arbitrary batches. Return a small number of semantic line ranges.

Return only JSON with this schema:
{
  "sections": [
    {
      "section_key": "related_work|method|experiment|appendix|conclusion",
      "start_line": 1,
      "end_line": 10,
      "confidence": 0.0,
      "rationale": "brief semantic evidence"
    }
  ]
}

Section outline:
{{section_outline}}
