<!-- stage:diagnose -->
You are diagnosing MinerU `full.md` output for an academic paper.

Use only the selected line-numbered evidence. Return only local issues that can be repaired by line-based patches.

Report these issue types only when the evidence is visible:
- `metadata_artifact`: fragmented title/authors/institutions. Target front matter is `Authors: ...` and `Institutions: ...`; omit emails.
- `heading_hierarchy`: numbered heading hierarchy is wrong. Use `## 5`, `### 5.1`, `#### 5.1.1`.
- `float_placement`: figure/table block interrupts a running sentence or paragraph.
- `caption_label`: figure/table caption is not a `> Figure ...` or `> Table ...` blockquote.
- `review_callout`: unresolved caption callout still uses `>[!Caution]`; use `>[!warning]`.
- `formula_delimiter`: visible TeX/math payload is missing Markdown math delimiters, e.g. `\Delta W _ { q }`, `equation_inline \Delta W _ { q } text`, `equation_inline A _ { r = 8 } text`, or bare `∆W`.
- `reading_order_disorder` or `ocr_artifact`: only for local, reversible parse artifacts.

Do not report:
- valid `## 5` followed by `### 5.1`;
- valid float blocks already between complete paragraphs;
- plain `equation_inline` placeholders only when no visible formula payload can be recovered;
- formulas already wrapped in `$...$` or `$$...$$`;
- issues requiring hidden lines or unavailable source context, except as `needs_review`.

Rules:
- Preserve all paper facts, citations, numbers, formulas, tables, image links, captions, and reference entries.
- Do not translate or rewrite prose.
- Formula delimiter issues inside captions are valid issues. One issue may cover a whole caption line when that line contains several `equation_inline ... text` payloads.
- Prefer fewer high-confidence issues; return at most 5.
- Return compact valid JSON only.

Additional operator instruction:
{{instruction}}

Known Paper metadata from Research-Flow. Use only for metadata repair:
{{metadata_json}}

Return only JSON:
{
  "source_hash": "{{source_hash}}",
  "issues": [
    {
      "issue_id": "issue_001",
      "type": "metadata_artifact|heading_ambiguous|heading_hierarchy|float_placement|caption_mixed|caption_label|review_callout|formula_delimiter|reading_order_disorder|ocr_artifact|needs_review",
      "start_line": 1,
      "end_line": 1,
      "severity": "low|medium|high",
      "confidence": 0.0,
      "description": "brief visible evidence",
      "suggested_action": "normalize_metadata|normalize_heading|move_float_block|split_caption|normalize_caption_label|normalize_review_callout|normalize_formula_delimiter|move_span|replace_span|mark_needs_review",
      "needs_pdf_context": false
    }
  ]
}

Line-numbered structural evidence:
{{line_numbered_markdown}}
<!-- /stage -->

<!-- stage:repair -->
You are repairing MinerU `full.md` output by emitting deterministic local JSON patches. Do not return Markdown.

Patch operations:
- `replace_span`: replace inclusive `start_line..end_line`.
- `insert_after`: insert after `start_line`.
- `delete_span`: delete inclusive `start_line..end_line`; use sparingly.
- `mark_needs_review`: no text change.

Repair rules:
- Keep patches small and evidence-backed.
- Preserve citations, numbers, formulas, tables, image links, captions, references, model names, dataset names, and technical terms.
- Metadata repair may normalize visible front matter to `Authors: ...` and `Institutions: ...`; omit emails and do not invent affiliations.
- Float repair may move a complete visible figure/table block to the nearest paragraph boundary.
- Caption repair must use `> Figure ...` or `> Table ...`; do not use localized labels or bold caption labels.
- Review callouts must use `>[!warning]`.
- Formula delimiter repair may only wrap visible TeX in Markdown math delimiters:
  - inline fragments in prose/captions use `$...$`, e.g. `\Delta W _ { q }` -> `$\Delta W _ { q }$`;
  - MinerU inline wrappers must be removed while preserving the payload, e.g. `equation_inline \Delta W _ { q } text` -> `$\Delta W _ { q }$`, `equation_inline A _ { r = 8 } text` -> `$A _ { r = 8 }$`, and `equation_inline ( r = 0 text )` -> `$( r = 0 )$`;
  - standalone formula lines or multi-line equations use `$$...$$`;
  - do not change symbols, spacing, subscripts, superscripts, numbers, or operators;
  - never leave partial repairs such as `$A$ text`, `$B$ text`, or any `equation_inline ... text` shell.
- If the same line also needs caption-label repair, emit one combined `replace_span` for that line instead of overlapping formula and caption patches.
- If a repair needs unavailable source context or hidden lines, use `mark_needs_review`.

Additional operator instruction:
{{instruction}}

Known Paper metadata from Research-Flow. Use only for metadata repair:
{{metadata_json}}

Return only JSON:
{
  "source_hash": "{{source_hash}}",
  "patches": [
    {
      "patch_id": "patch_001",
      "issue_id": "issue_001",
      "op": "replace_span|insert_after|delete_span|mark_needs_review",
      "start_line": 1,
      "end_line": 1,
      "replacement": "Markdown replacement text",
      "confidence": 0.0,
      "rationale": "brief reason"
    }
  ]
}

Diagnosis JSON:
{{diagnosis_json}}

Line-numbered structural evidence:
{{line_numbered_markdown}}
<!-- /stage -->

<!-- stage:verify -->
You are verifying a MinerU Markdown refinement. Do not rewrite the paper.

Check preservation of citations, numbers, formulas, tables, image links, captions, references, title, authors, institutions, model names, and dataset names. Verify that figure/table blocks are not inside running sentences, captions use `> Figure ...` / `> Table ...`, unresolved callouts use `>[!warning]`, and formula delimiter repairs only add `$` or `$$` around existing TeX/math payloads. MinerU `equation_inline ... text` wrappers may be removed only when converted to math. Treat `$A$ text`, `$B$ text`, or remaining `equation_inline ... text` in accepted replacement lines as unresolved formula-wrapper defects.

Treat local preservation checks as authoritative. Return `warning` for unresolved visual-context items and `fail` only for likely content loss, invented metadata, destructive table/caption/reference changes, or hierarchy regression.

Additional operator instruction:
{{instruction}}

Return only JSON:
{
  "source_hash": "{{source_hash}}",
  "status": "pass|warning|fail",
  "summary": "one sentence",
  "blocking_issues": [],
  "review_items": []
}

Patch apply report:
{{patch_apply_report_json}}

Verification context:
{{verify_context}}
<!-- /stage -->

<!-- stage:default -->
Legacy fallback for MinerU Markdown refinement.

Make only conservative local Markdown repairs:
- preserve factual content, equations, citations, tables, references, and image links;
- normalize headings, visible front matter, figure/table placement, captions, callouts, and formula delimiters;
- do not summarize, translate, add claims, or remove technical details.

Additional operator instruction:
{{instruction}}

{{markdown}}
<!-- /stage -->
