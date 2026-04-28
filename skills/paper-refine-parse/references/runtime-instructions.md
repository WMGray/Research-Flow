<!-- stage:diagnose -->
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

Non-issues that must not be returned:
- `## 5` followed later by `### 5.1`; these are different Markdown levels and are already valid.
- `### 5.1` or `### 5.4` under `## 5`; do not claim these are at the same level as the parent.
- A blockquoted caption using `图注`, `鍥炬敞`, `Figure`, `Table`, or `equation_inline` placeholders unless it is visibly merged with unrelated prose. `equation_inline` placeholders are source evidence; do not report them just to remove or rewrite them.
- Any candidate whose description would say "valid", "correct", "check only", or "no change needed".

Diagnosis rubric:
- Treat the input as evidence windows, not as the whole paper. A missing nearby line is not evidence that a section is absent.
- `metadata_artifact`: use only early metadata lines and supplied metadata. Repair spacing, punctuation, and line-break artifacts only when the visible text already contains the same title/author tokens.
- `heading_hierarchy`: infer hierarchy from numbering first, Markdown level second. `5` is a parent, `5.1` is a child, and `5.1.1` is deeper even if MinerU gave them the same Markdown level.
- Canonical numbered Markdown levels are `## 5`, `### 5.1`, and `#### 5.1.1`. A line like `### 5.1 BASELINES` under `## 5 EMPIRICAL EXPERIMENTS` is already valid and must not be reported.
- `heading_ambiguous`: report only when the line is locally isolated and looks like a real paper heading by numbering, typography artifact, or surrounding structure. Do not convert body sentences into headings.
- `caption_mixed`: report when a Figure/Table caption is visibly glued to body prose, another caption, a list item, or a table block. Do not move captions across pages without visual evidence.
- A localized or garbled caption label such as `图注`, `鍥炬敞`, or `Figure` is not by itself `caption_mixed`; preserve caption labels and wording unless the caption is visibly merged with unrelated text.
- `reading_order_disorder`: report only when adjacent line evidence shows a reversible local ordering problem. If the correct order needs page layout or images, use `needs_pdf_context=true`.
- `ocr_artifact`: report only local artifacts such as broken hyphenation, repeated glyph fragments, or corrupted line joins. Do not "improve" author wording or scientific prose.

Rules:
- Preserve paper facts. Never infer missing scientific content.
- Do not split the paper into arbitrary batches.
- Do not assume existing section boundaries are reliable.
- Do not report a missing section merely because surrounding full-text lines are not shown.
- Do not return issues for structures that are already correct. If the description says a heading or caption is correct, omit the issue entirely.
- Do not normalize valid Markdown heading levels just for style; downstream code can read `#`, `##`, and deeper headings.
- Do report invalid heading hierarchy when a numbered child section has the same Markdown level as its parent.
- Do report author/title metadata only when the evidence shows local spacing or punctuation artifacts; never invent missing names or affiliations.
- Do not patch truncated evidence lines unless the safe action is `mark_needs_review`.
- Do not remove parser placeholders such as `equation_inline` by guessing the intended formula; that requires PDF or math context.
- If a change would require PDF visual context, set `needs_pdf_context=true`.
- Prefer fewer, high-confidence issues. Leave uncertain cases to review.
- Do not fill the five issue slots. If only one real issue is visible, return one issue.
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
<!-- /stage -->

<!-- stage:repair -->
You are repairing MinerU `full.md` output for an academic paper by emitting local patches.

Input includes selected line-numbered structural evidence and a diagnosis JSON. Return only deterministic, line-based JSON patches. Do not return the full rewritten paper.

Patch rules:
- `replace_span`: replace inclusive `start_line..end_line` with `replacement`.
- `insert_after`: insert `replacement` after `start_line`.
- `delete_span`: delete inclusive `start_line..end_line`; use sparingly.
- `mark_needs_review`: no text change; use when visual PDF context is required.
- Preserve citations, numbers, formulas, tables, image links, captions, and technical terms.
- Preserve author identity exactly; only repair visible spacing/punctuation artifacts in names or affiliations.
- Parent/child section hierarchy must follow numbering: `## 5`, `### 5.1`, and `#### 5.1.1`. Do not change `### 5.1` to `#### 5.1` when its parent is `## 5`.
- A patch must not summarize, translate, or add scientific claims.
- Replacement text must be complete Markdown for the target span.
- Do not patch evidence lines marked as truncated. Use `mark_needs_review` when the full line is needed.
- Use confidence < 0.65 only when you want the patch engine to reject or route to review.

Repair policy:
- Prefer no text patch over a speculative patch. The backend also runs deterministic normalization after LLM patches.
- Emit one patch per accepted issue. Keep spans as small as possible and do not combine unrelated issues.
- If a diagnosis item is actually a non-issue, omit the patch entirely; do not emit `mark_needs_review`.
- For `metadata_artifact`, only fix visible tokenization artifacts. Never add, remove, reorder, or romanize authors unless the same tokens are already visible.
- For `heading_hierarchy`, change only Markdown heading markers or the minimum heading line text needed to express the visible numbering. Do not rename sections.
- For `caption_mixed`, split caption/prose only when both parts are fully visible in the selected span. Preserve image links and table rows exactly.
- Do not translate caption labels or caption wording. Keep `图注`, `鍥炬敞`, `Figure`, and table labels as source text unless the issue is a visible merge/split problem.
- Do not replace or delete `equation_inline` placeholders in captions. If the placeholder needs mathematical recovery, omit the patch or use `mark_needs_review`.
- For `reading_order_disorder`, use `move_span` only through supported operations (`delete_span` plus `insert_after`) when the complete moved text is visible. Otherwise use `mark_needs_review`.
- For `mark_needs_review`, keep `replacement` as an empty string and put the uncertainty in `rationale`. Do not use `mark_needs_review` for "no patch needed"; omit that patch instead.

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
<!-- /stage -->

<!-- stage:verify -->
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
<!-- /stage -->

<!-- stage:default -->
Legacy single-call fallback for MinerU Markdown refinement.

Prefer the current diagnose -> repair -> verify patch workflow when it is available. If this prompt is used directly, make only conservative local Markdown repairs for downstream paper processing.

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
<!-- /stage -->
