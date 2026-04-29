---
name: get-code-context-exa
description: Use when the user needs authoritative programming examples, API syntax, library documentation, configuration patterns, or debugging snippets from GitHub, Stack Overflow, and technical docs through Exa code context search. Prefer this skill for coding questions that benefit from real-world snippets and source links.
---

# Code Context (Exa)

Use the Exa code-context MCP tool to find real code snippets and documentation for programming tasks.

## Tool restriction

Only use `get_code_context_exa` from the `exa` MCP server.
Do not use other Exa tools when this skill is active.

## When to use

Use this skill for programming-related requests such as:

- API usage and syntax
- SDK or library examples
- Config and setup patterns
- Framework how-to questions
- Debugging that needs authoritative snippets

## Query construction

Write high-signal queries:

- Always include the programming language.
- Include the framework and version when relevant, for example `Next.js 14`, `React 19`, or `Python 3.12`.
- Include exact identifiers when available: function names, class names, config keys, CLI flags, or error messages.
- Prefer precise problem statements over broad keywords.

Examples:

- `Python 3.12 httpx retry transport example`
- `TypeScript React 19 useDeferredValue search input example`
- `Go generics constraint interface comparable example`
- `Next.js 14 Route Handler cookies set example`

## Token budget

Choose `tokensNum` based on scope:

- Focused snippet: `1000-3000`
- Most requests: `5000`
- Complex integration: `10000-20000`

Avoid requesting more context than needed.

## Context discipline

Prefer to keep Exa lookups isolated from the main reasoning flow.

- If delegated or parallel agent work is explicitly allowed in the current run, use a spawned sub-agent for the lookup.
- Have that sub-agent call `get_code_context_exa`, extract only the minimum viable snippet, note version constraints, and deduplicate mirrors or near-identical answers before returning.
- If sub-agents are not available or not allowed, keep the query narrow and return only the minimum snippet set.

## Output requirements

Return:

1. Minimal working snippet or snippets that are easy to copy
2. Notes about versions, constraints, or gotchas
3. Source links from the returned context

Before answering:

- Deduplicate repeated results from mirrors, forks, or repeated answers
- Keep only the best representative snippet for each approach
- Prefer official docs and upstream repositories when quality is similar

## Workflow

1. Identify the exact programming task and required ecosystem.
2. Build a precise query with language plus framework or version.
3. Call `get_code_context_exa` with a tight `tokensNum`.
4. Extract only the most useful snippet or snippets.
5. Add short notes for constraints and source provenance.

## MCP expectation

This skill expects the `exa` MCP server to be configured with the code-context endpoint so that `get_code_context_exa` is the available Exa tool.
