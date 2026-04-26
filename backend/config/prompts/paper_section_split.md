You are planning canonical section extraction for an academic paper Markdown file.

You receive heading evidence from the complete `parsed/refined.md`. Do not rewrite or summarize the paper. Return only line ranges for the four canonical Research-Flow sections.

Canonical section keys:
- `related_work`: prior work, background, literature context.
- `method`: main approach, model, algorithm, system, theoretical method.
- `experiment`: experiments, evaluation, empirical setup, results, ablations.
- `conclusion`: conclusion, limitations, future work.

Rules:
- Use full line ranges from the refined Markdown, inclusive.
- Treat numbered child headings like `5.1`, `5.2`, `A.1` as children of their nearest major heading unless the outline clearly shows a new top-level section.
- Do not classify a child heading as a canonical section just because its label contains words like "method" or "experiment".
- Prefer major headings where `major=true`.
- If MinerU made parent and child headings the same Markdown level, trust the numbering hierarchy rather than the Markdown level.
- A canonical range should normally start at the major heading that owns the section and end immediately before the next major heading that is not its child.
- Related work may be absent in short papers; omit it if there is no explicit background/prior-work section.
- Method ranges should include approach/model/algorithm/system/theory subsections under the method parent.
- Experiment ranges should include setup, datasets, metrics, baselines, results, ablations, and analysis under the experiment parent.
- Conclusion ranges may include limitations or future work only when they are part of the conclusion/discussion area.
- Exclude References, Acknowledgments, Appendix, author affiliations, and metadata unless they are clearly part of a canonical section body.
- If evidence is insufficient for a section, omit it instead of guessing.
- Use confidence below 0.65 for uncertain ranges so the backend rejects them.
- Do not split the paper into arbitrary batches. Use the known outline and return only canonical ranges.

Return only JSON with this schema:
{
  "sections": [
    {
      "section_key": "related_work|method|experiment|conclusion",
      "start_line": 1,
      "end_line": 10,
      "confidence": 0.0,
      "rationale": "brief heading evidence"
    }
  ]
}

Section outline:
{{section_outline}}
