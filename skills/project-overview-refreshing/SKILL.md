---
name: project-overview-refreshing
description: Maintain Research-Flow Project overview refresh contracts. Use when changing Project overview statistics, deterministic managed block output, refresh-overview task behavior, RF block write-back rules, or `project_overview_refreshing.default` runtime instructions.
---

# Project Overview Refreshing

## Core Rule

Refresh `overview.md` from trusted Project metadata only. Do not call an LLM, infer missing values, or modify user-authored text outside managed RF blocks.

## Inputs

Use only supplied runtime context:

- Project identity, status, owner, timestamps, and summary.
- Linked paper, Knowledge, Dataset, Presentation, and experiment counts.
- Recent Project job records and current document versions.
- Existing `overview.md` content, including RF block metadata.

## Output Blocks

Write exactly this managed block when data is available:

- `overview_stats`: Markdown table of current Project statistics and recent activity.

If a value is unavailable, write the configured missing-value label instead of guessing.

## Workflow

1. Read `references/io-contract.md` before changing backend payloads or block IDs.
2. Build the `overview_stats` Markdown table deterministically from the supplied fields.
3. Preserve the existing `RF:BLOCK_START/END` marker format and update only `managed="true"` blocks.
4. Leave `managed="false"` blocks and free-form user content unchanged.
5. Keep row names stable so frontend diffs remain readable.

## Runtime Reference

Use `references/runtime-instructions.md` for the runtime prompt or deterministic formatter contract behind `project_overview_refreshing.default`.

## Validation

Run focused Project task tests after changes:

```powershell
python -m pytest backend\tests -q
```
