<!-- prompt:diagnose -->
You are diagnosing MinerU `full.md` output for an academic paper.

Input is selected line-numbered structural evidence from the complete paper. Do not rewrite the paper. Identify only local, evidence-backed parsing issues that can be repaired by a deterministic patch engine.

Focus on common MinerU failure modes:
- title, author, affiliation, or abstract metadata spacing artifacts
- ambiguous or missing section headings
- incorrect heading hierarchy, especially numbered child headings such as `5.1` rendered at the same level as `5`
- figure/table captions mixed into body text
- body text merged into captions or lists
- reading-order disorder between nearby paragraphs
- obvious OCR/layout artifacts

Diagnosis rubric:
- Treat the input as evidence windows, not as the whole paper. A missing nearby line is not evidence that a section is absent.
- `metadata_artifact`: use only early metadata lines and supplied metadata. Repair spacing, punctuation, and line-break artifacts only when the visible text already contains the same title/author tokens.
- `heading_hierarchy`: infer hierarchy from numbering first, Markdown level second. `5` is a parent, `5.1` is a child, and `5.1.1` is deeper even if MinerU gave them the same Markdown level.
- `heading_ambiguous`: report only when the line is locally isolated and looks like a real paper heading by numbering, typography artifact, or surrounding structure. Do not convert body sentences into headings.
- `caption_mixed`: report when a Figure/Table caption is visibly glued to body prose, another caption, a list item, or a table block. Do not move captions across pages without visual evidence.
- `reading_order_disorder`: report only when adjacent line evidence shows a reversible local ordering problem. If the correct order needs page layout or images, use `needs_pdf_context=true`.
- `ocr_artifact`: report only local artifacts such as broken hyphenation, repeated glyph fragments, or corrupted line joins. Do not "improve" author wording or scientific prose.

Rules:
- Preserve paper facts. Never infer missing scientific content.
- Do not split the paper into arbitrary batches.
- Do not assume existing section boundaries are reliable.
- Do not report a missing section merely because surrounding full-text lines are not shown.
- Do not normalize valid Markdown heading levels just for style; downstream code can read `#`, `##`, and deeper headings.
- Do report invalid heading hierarchy when a numbered child section has the same Markdown level as its parent.
- Do report author/title metadata only when the evidence shows local spacing or punctuation artifacts; never invent missing names or affiliations.
- Do not patch truncated evidence lines unless the safe action is `mark_needs_review`.
- If a change would require PDF visual context, set `needs_pdf_context=true`.
- Prefer fewer, high-confidence issues. Leave uncertain cases to review.
- Return at most 5 issues, ordered by severity and confidence.
- Keep each `description` and `suggested_action` under 120 characters.
- Return compact valid JSON. Do not include Markdown fences, comments, trailing commas, or long copied evidence.

Additional operator instruction:
{{instruction}}

Known Paper metadata from Research-Flow. Use only for title/author metadata repair; do not use it to invent scientific content:
{{metadata_json}}

Return only JSON with this schema:
{
  "source_hash": "{{source_hash}}",
  "issues": [
    {
      "issue_id": "issue_001",
      "type": "metadata_artifact|heading_ambiguous|heading_hierarchy|caption_mixed|reading_order_disorder|ocr_artifact|needs_review",
      "start_line": 1,
      "end_line": 1,
      "severity": "low|medium|high",
      "confidence": 0.0,
      "description": "brief evidence from the input",
      "suggested_action": "normalize_metadata|normalize_heading|split_caption|move_span|replace_span|mark_needs_review",
      "needs_pdf_context": false
    }
  ]
}

Line-numbered structural evidence:
{{line_numbered_markdown}}
<!-- /prompt -->

<!-- prompt:repair -->
You are repairing MinerU `full.md` output for an academic paper by emitting local patches.

Input includes selected line-numbered structural evidence and a diagnosis JSON. Return only deterministic, line-based JSON patches. Do not return the full rewritten paper.

Patch rules:
- `replace_span`: replace inclusive `start_line..end_line` with `replacement`.
- `insert_after`: insert `replacement` after `start_line`.
- `delete_span`: delete inclusive `start_line..end_line`; use sparingly.
- `mark_needs_review`: no text change; use when visual PDF context is required.
- Preserve citations, numbers, formulas, tables, image links, captions, and technical terms.
- Preserve author identity exactly; only repair visible spacing/punctuation artifacts in names or affiliations.
- Parent/child section hierarchy must follow numbering: `5` is a major heading, `5.1` is a child heading, `5.1.1` is a deeper child.
- A patch must not summarize, translate, or add scientific claims.
- Replacement text must be complete Markdown for the target span.
- Do not patch evidence lines marked as truncated. Use `mark_needs_review` when the full line is needed.
- Use confidence < 0.65 only when you want the patch engine to reject or route to review.

Repair policy:
- Prefer no text patch over a speculative patch. The backend also runs deterministic normalization after LLM patches.
- Emit one patch per accepted issue. Keep spans as small as possible and do not combine unrelated issues.
- For `metadata_artifact`, only fix visible tokenization artifacts. Never add, remove, reorder, or romanize authors unless the same tokens are already visible.
- For `heading_hierarchy`, change only Markdown heading markers or the minimum heading line text needed to express the visible numbering. Do not rename sections.
- For `caption_mixed`, split caption/prose only when both parts are fully visible in the selected span. Preserve image links and table rows exactly.
- For `reading_order_disorder`, use `move_span` only through supported operations (`delete_span` plus `insert_after`) when the complete moved text is visible. Otherwise use `mark_needs_review`.
- For `mark_needs_review`, keep `replacement` as an empty string and put the uncertainty in `rationale`.

Additional operator instruction:
{{instruction}}

Known Paper metadata from Research-Flow. Use only for title/author metadata repair; do not use it to invent scientific content:
{{metadata_json}}

Return only JSON with this schema:
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
<!-- /prompt -->

<!-- prompt:verify -->
You are verifying a MinerU Markdown refinement for an academic paper.

Compare the deterministic patch report and verification context. You are not allowed to rewrite the paper. Report whether the refinement preserved scientific content and improved parse structure.

Check specifically:
- citations and reference markers are preserved
- numbers, metrics, years, dataset names, and model names are preserved
- title, author names, affiliations, and emails are not lost or invented
- formulas, tables, image links, figure/table captions are preserved
- numbered heading hierarchy is coherent: child headings such as `5.1` stay under parent `5`
- heading structure is more useful without inventing sections
- no summarization, translation, or new claims were introduced
- rejected patches are acceptable or should block review
- if no text patch was applied and local preservation checks are authoritative, return `pass` unless the patch report itself shows a blocking risk

Self-audit policy:
- Treat local preservation checks as authoritative for exact counts of citations, numbers, formulas, image links, and length.
- A structural improvement is valid only if it changes Markdown organization without changing paper claims.
- Warn, rather than fail, when only review items remain and no destructive text change was applied.
- Fail only for likely content loss, invented metadata, unsafe section invention, destructive caption/table changes, or a clear hierarchy regression.
- Mention unresolved visual-context items in `review_items`; do not ask to rewrite the paper.

Additional operator instruction:
{{instruction}}

Return only JSON with this schema:
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
<!-- /prompt -->

<!-- prompt:default -->
Legacy single-call fallback for MinerU Markdown refinement.

Prefer the current diagnose -> repair -> verify patch workflow when it is available. If this prompt is used directly, make only conservative local Markdown repairs for downstream section splitting.

Requirements:
- Preserve all factual content, equations, citations, tables, and image links.
- Normalize heading levels and remove obvious OCR or layout artifacts.
- Do not summarize, translate, add new content, or remove technical details.
- Do not rewrite the whole paper for style.
- Preserve author identity exactly; only repair visible spacing or punctuation artifacts.
- Keep numbered hierarchy coherent: `5` is a parent, `5.1` is a child, and `5.1.1` is deeper.
- Leave uncertain figure/table/text layering issues unchanged rather than guessing.
- Return only Markdown, with no explanations outside the Markdown.

Additional operator instruction:
{{instruction}}

{{markdown}}
<!-- /prompt -->
