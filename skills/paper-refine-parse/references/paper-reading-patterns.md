# Paper Reading Patterns

Use this reference when improving Research-Flow's paper refine, split, and note prompts.

## Sources reviewed

- `claude-scholar`: research lifecycle skills, `paper-miner`, `ml-paper-writing`, Zotero/Obsidian paper note schemas, and section self-review checklists.
- `AI-paper-reading`: PDF -> layout detection -> figure/table matching -> LLM selection -> outline planning -> per-figure explanation -> Markdown composition.

## Transferable patterns

1. Schema-first control
   - LLMs should return control data: issue lists, line patches, section ranges, selected figures, note blocks.
   - Backend code owns patch application, validation, persistence, and rejection.

2. Evidence-grounded reading
   - Prompts should name the supplied evidence boundary.
   - If the evidence is a structural window, the LLM must not infer missing sections.
   - If visual layout is required, route to review rather than inventing a fix.

3. Section-aware, not batch-based
   - Papers have a semantic outline. Do not chunk by token budget when the outline is available.
   - Child headings such as `5.1` remain inside their parent section unless the outline proves otherwise.
   - Canonical extraction should return line ranges, not rewritten text.

4. Figure/table role awareness
   - Figure/table content has roles: problem, method, result, support.
   - Caption/body/table mixing is a parsing problem; it should be repaired only when local evidence is complete.
   - Important figures and tables should influence summaries only when their text or image-derived evidence is available.

5. Durable paper note schema
   - Notes should separate research question, method, contribution, evidence, limitation, and project relevance.
   - Summaries must preserve source attribution and uncertainty.
   - Do not dump raw full text into notes.

## Prompt design rules for this project

- Keep prompts JSON-only where the runtime expects JSON.
- Include `source_hash` in refine stages.
- Prefer small, high-confidence patches over broad rewrites.
- Preserve citations, numbers, formulas, image links, tables, captions, model names, dataset names, and author identity.
- Make verification a self-audit over patch reports and local preservation checks.
- Record rejected/uncertain items in review artifacts rather than silently accepting them.
