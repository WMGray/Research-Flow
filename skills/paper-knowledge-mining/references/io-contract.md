# I/O Contract

`assets/examples/` contains examples only.

## Input Fields

| Field | Required | Meaning |
|---|---:|---|
| `metadata.paper_id` | no | Source Paper id |
| `metadata.title` | yes | Source Paper title |
| `metadata.authors` | no | Paper authors |
| `metadata.year` | no | Publication year |
| `metadata.venue` | no | Venue |
| `sections[]` | yes | Canonical section content |
| `note` | no | Generated or human-edited note |

## Output Fields

| Field | Required | Meaning |
|---|---:|---|
| `items[]` | yes | Extracted knowledge items |
| `title` | yes | Brief English title |
| `knowledge_type` | yes | `view` or `definition` |
| `category_label` | yes | Allowed category from `SKILL.md` |
| `summary_zh` | yes | Chinese summary |
| `original_text_en` | conditional | Required for `view`; nullable for weak definition evidence |
| `citation_marker` | no | Exact marker such as `[32]` |
| `research_field` | no | Field label |
| `source_section` | yes | Canonical source section |
| `source_locator` | yes | Re-findable locator |
| `evidence_text` | yes | Verbatim input evidence |
| `confidence_score` | yes | Evidence confidence |

## Rules

- Extract only evidence-supported views and definitions.
- Do not infer the earliest origin of an idea.
- Copy citation markers exactly.
- Use `confidence_score < 0.6` for weak evidence.
