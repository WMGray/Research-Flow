# I/O Contract

`assets/examples/` contains examples only.

## Input Fields

| Field | Required | Meaning |
|---|---:|---|
| `metadata.title` | yes | Paper title |
| `metadata.authors` | yes | Paper authors |
| `metadata.year` | no | Publication year |
| `metadata.venue` | no | Venue |
| `source_hash` | yes | Stable hash of source markdown |
| `markdown` | yes | MinerU/raw paper Markdown |

## Output Fields

| Field | Required | Meaning |
|---|---:|---|
| `source_hash` | yes | Must match input |
| `diagnosis.issues[]` | yes | Structured issues with line ranges |
| `patches[]` | yes | Line-based patches |
| `verify.status` | yes | `pass`, `warning`, or `fail` |
| `verify.blocking_issues[]` | yes | Blocking verification failures |
| `verify.review_items[]` | yes | Human review items |
| `refined_markdown` | yes | Locally safe refined Markdown |

## Rules

- Preserve citations, numbers, formulas, tables, image links, captions, model names, dataset names, and technical terms.
- Do not rewrite the whole paper for style.
- Use `mark_needs_review` when visual PDF context is required.
