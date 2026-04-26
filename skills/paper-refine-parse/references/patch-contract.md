# Patch Contract

## Diagnosis JSON

```json
{
  "source_hash": "sha256-of-raw-markdown",
  "issues": [
    {
      "issue_id": "issue_001",
      "type": "heading_ambiguous",
      "start_line": 12,
      "end_line": 12,
      "severity": "medium",
      "confidence": 0.91,
      "description": "The heading is present as plain text.",
      "suggested_action": "normalize_heading",
      "needs_pdf_context": false
    }
  ]
}
```

## Patch JSON

Supported operations:

- `replace_span`: replace inclusive `start_line..end_line`.
- `insert_after`: insert replacement after `start_line`.
- `delete_span`: delete inclusive `start_line..end_line`; use sparingly.
- `mark_needs_review`: no text change; creates a review item.

Patch policy:

- Patches are local repairs, not paper rewrites.
- One patch should address one diagnosis issue.
- Replacement text must preserve all visible scientific content in the target span.
- Use `mark_needs_review` when the correction needs PDF visual context, missing hidden lines, or ambiguous reading order.
- For `mark_needs_review`, `replacement` may be an empty string.
- Parent/child heading hierarchy follows section numbering before Markdown level.

```json
{
  "source_hash": "sha256-of-raw-markdown",
  "patches": [
    {
      "patch_id": "patch_001",
      "issue_id": "issue_001",
      "op": "replace_span",
      "start_line": 12,
      "end_line": 12,
      "replacement": "## 1 Introduction",
      "confidence": 0.95,
      "rationale": "Normalize the section heading."
    }
  ]
}
```

## Verification JSON

```json
{
  "source_hash": "sha256-of-raw-markdown",
  "status": "pass",
  "summary": "The refinement preserves technical content.",
  "blocking_issues": [],
  "review_items": []
}
```

The backend still runs local preservation checks. LLM `pass` cannot override missing citations, numbers, formulas, image links, or destructive length changes.

## Deterministic Normalization Artifact

LLM patches are not the only valid source of refinement. After patch application,
the backend may apply safe deterministic normalization and must write:

```json
{
  "source_hash": "sha256-of-raw-markdown",
  "input_hash": "sha256-before-normalization",
  "output_hash": "sha256-after-normalization",
  "changed": true,
  "operation_count": 2,
  "operations": [
    {
      "operation_id": "det_0001",
      "operation_type": "normalize_heading_level",
      "line_no": 42,
      "before": "# 5.1 METHOD DETAILS",
      "after": "### 5.1 METHOD DETAILS",
      "rationale": "Convert a paper section marker to stable Markdown heading syntax."
    }
  ]
}
```

## Section Split Plan JSON

LLM section splitting is allowed only as control data. It must return canonical
line ranges, not rewritten text:

```json
{
  "sections": [
    {
      "section_key": "method",
      "start_line": 40,
      "end_line": 120,
      "confidence": 0.91,
      "rationale": "Major heading 4 OUR METHOD starts here."
    }
  ]
}
```

The backend rejects unknown keys, confidence below `0.65`, invalid ranges, and
overlapping ranges. Child headings such as `5.1` must stay under parent `5`.

## Reading Note Contract

Paper notes generated after splitting must be evidence-grounded:

- use only supplied canonical section text;
- separate research question, method, contribution, evidence, and limitation;
- preserve numbers, dataset names, method names, and citations when present;
- mark missing or parser-uncertain content explicitly instead of filling gaps.
