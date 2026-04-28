---
name: project-method-drafting
description: Maintain Research-Flow Project method drafting contracts. Use when changing Project method generation, core hypothesis drafts, innovation point blocks, design risk blocks, linked-paper method synthesis, or `project_method_drafting.default`.
---

# Project Method Drafting

## Core Rule

Draft Project method blocks from linked evidence and current Project notes. Separate proposed design ideas from validated facts, and make uncertainty visible.

## Inputs

Use supplied context:

- Current `related-work.md` and `method.md` content.
- Linked paper `note.md` method blocks and relevant `parsed/sections/method.md` snippets.
- Relationship roles, especially `method_reference`, `inspiration`, and `baseline`.
- Optional Knowledge summaries and user focus instructions.

## Output Blocks

Return these managed blocks:

- `method_draft`: core hypothesis, technical route, and module decomposition.
- `innovation_points`: candidate novelty claims with evidence and caveats.
- `design_risks`: technical risks, missing assumptions, and mitigation ideas.

## Workflow

1. Read `references/io-contract.md` before changing task, feature, or block contracts.
2. Use `references/runtime-instructions.md` for the LLM runtime prompt.
3. Ground method claims in linked papers or Project notes.
4. Label speculative design as proposal, not established fact.
5. Keep claims modular so users can edit or lock individual RF blocks later.
6. Preserve locked and free-form user content during write-back.

## Runtime Reference

The runtime instruction for `project_method_drafting.default` is `references/runtime-instructions.md`.

## Validation

Run focused Project task tests after changes:

```powershell
python -m pytest backend\tests -q
```
