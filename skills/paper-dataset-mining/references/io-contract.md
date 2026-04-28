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

## Output Fields

| Field | Required | Meaning |
|---|---:|---|
| `items[]` | yes | Dataset or benchmark mentions |
| `dataset_name` | yes | Dataset or benchmark name |
| `task` | no | Task name |
| `modality` | no | `text`, `image`, `audio`, `video`, `multimodal`, `tabular`, `graph`, `other`, or null |
| `scale` | no | Stated size |
| `split_rule` | no | Stated split |
| `metrics` | yes | Metric names; may be empty |
| `source_url` | no | Stated URL |
| `doi` | no | Stated DOI |
| `license` | no | Stated license |
| `description_zh` | yes | Chinese description |
| `citation_marker` | no | Exact marker such as `[32]` |
| `source_section` | yes | Canonical source section |
| `source_locator` | yes | Re-findable locator |
| `evidence_text` | yes | Verbatim input evidence |
| `confidence_score` | yes | Evidence confidence |

## Rules

- Extract only datasets or benchmarks stated in the input.
- Do not infer missing URL, DOI, license, scale, split, or metric values.
- Copy citation markers exactly.
- Use `confidence_score < 0.6` for weak evidence.
