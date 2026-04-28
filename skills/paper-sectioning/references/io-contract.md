# I/O Contract

`assets/examples/` contains examples only.

## Input Fields

| Field | Required | Meaning |
|---|---:|---|
| `source_hash` | yes | Stable hash of refined markdown |
| `section_outline` | yes | Line-numbered heading/snippet outline |

## Output Fields

| Field | Required | Meaning |
|---|---:|---|
| `source_hash` | yes | Must match input |
| `sections[]` | yes | Section line-range plan |
| `sections[].section_key` | yes | `related_work`, `method`, `experiment`, `appendix`, or `conclusion` |
| `sections[].start_line` | yes | 1-based inclusive start line |
| `sections[].end_line` | yes | 1-based inclusive end line |
| `sections[].confidence` | yes | Range confidence |
| `sections[].rationale` | yes | Short reason |

## Rules

- Exclude References, Bibliography, Acknowledgments, affiliations, parser metadata, and boilerplate.
- Keep Appendix content under `appendix`, including content after References.
- Use `confidence < 0.65` for uncertain ranges.
