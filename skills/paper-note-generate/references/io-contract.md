# I/O Contract

`assets/examples/` contains examples only.

## Input Fields

| Field | Required | Meaning |
|---|---:|---|
| `metadata.title` | yes | Paper title |
| `metadata.authors` | no | Paper authors |
| `metadata.year` | no | Publication year |
| `metadata.venue` | no | Venue |
| `metadata.doi` | no | DOI |
| `sections[]` | yes | Canonical section content |
| `sections[].section_key` | yes | `related_work`, `method`, `experiment`, `appendix`, or `conclusion` |
| `sections[].title` | no | Section title |
| `sections[].content` | yes | Section text |
| `figures[]` | no | Resolved figure/table evidence |

## Output Fields

| Field | Required | Meaning |
|---|---:|---|
| `blocks.paper_overview` | yes | Overview block |
| `blocks.terminology_guide` | yes | Terms block |
| `blocks.background_motivation` | yes | Background block |
| `blocks.experimental_setup` | yes | Setup block |
| `blocks.method` | yes | Method block |
| `blocks.experimental_results` | yes | Results block |

Rendered Markdown must wrap the same six block ids with `RF:BLOCK_START` / `RF:BLOCK_END`.

## Rules

- Do not repeat renderer-owned top-level headings inside block content.
- Inner headings start at `###`.
- Preserve exact Figure/Table numbers and image paths from input.
- State missing evidence explicitly instead of guessing.
