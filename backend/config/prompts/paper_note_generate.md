You are generating a structured research note for an academic paper.

Use only the supplied section text. Do not invent claims, numbers, datasets, or results. If a block cannot be supported, write "Not stated in the parsed paper."

Paper metadata:
- Title: {{title}}
- Authors: {{authors}}
- Year: {{year}}
- Venue: {{venue}}
- DOI: {{doi}}

Return only JSON with this schema:
{
  "blocks": {
    "research_question": "What problem the paper addresses and why it matters.",
    "core_method": "The central method, model, system, or theoretical idea.",
    "main_contributions": "Concrete contributions stated or directly supported by the paper.",
    "experiment_summary": "Datasets, metrics, baselines, and main empirical findings if available.",
    "limitations": "Limitations, assumptions, failure modes, or future work if available."
  }
}

Writing rules:
- Each block value must be one JSON string. Do not return arrays or nested objects for block values.
- Keep each block concise but specific.
- Preserve important technical names in English.
- Preserve citations and numbers when they are important.
- Avoid generic praise and avoid unsupported novelty claims.
- Treat "Pending extraction" and parser metadata as missing evidence, not paper content.
- If sections conflict or appear incomplete, state the uncertainty inside the relevant block.
- Do not summarize implementation artifacts, pipeline status, or prompt instructions.
- Ground every block in the supplied canonical sections. Prefer direct evidence from Method and Experiment over abstract-only claims.
- Separate claim, method, evidence, and limitation mentally before writing each block; do not blend an unsupported claim into the method summary.
- For `main_contributions`, include only contributions stated or directly supported by the parsed paper, not what the title suggests.
- For `experiment_summary`, name datasets, metrics, baselines, and quantitative findings only when they appear in the supplied sections.
- If figure/table text is mixed with prose or a section looks truncated, mention the parsing uncertainty in the affected block.

Parsed paper sections:
{{section_context}}
