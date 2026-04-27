from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from core.pdf_parser_config import MarkdownRefineConfig
from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse


MARKDOWN_PLACEHOLDERS = ("{{markdown}}", "{markdown}")


class LLMGenerateClient(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate an LLM response for a configured feature."""


@dataclass(frozen=True, slots=True)
class MarkdownRefineResult:
    markdown_path: Path
    refined: bool
    error: str | None = None


def build_markdown_refine_request_content(instructions: str, markdown_text: str) -> str:
    for placeholder in MARKDOWN_PLACEHOLDERS:
        if placeholder in instructions:
            return instructions.replace(placeholder, markdown_text)
    return f"{instructions.rstrip()}\n\n<markdown>\n{markdown_text}\n</markdown>"


def resolve_markdown_refine_instructions(config: MarkdownRefineConfig) -> str:
    if config.instruction_override.strip():
        return config.instruction_override
    from ..skill_runtime import load_skill_runtime_instructions

    return load_skill_runtime_instructions(config.runtime_instruction_key)


def strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


async def refine_markdown_with_llm(
    *,
    markdown_path: Path,
    output_path: Path,
    config: MarkdownRefineConfig,
    llm_client: LLMGenerateClient,
) -> MarkdownRefineResult:
    if not config.enabled:
        return MarkdownRefineResult(markdown_path=markdown_path, refined=False)

    markdown_text = markdown_path.read_text(encoding="utf-8")
    if not markdown_text.strip():
        return MarkdownRefineResult(markdown_path=markdown_path, refined=False, error="source markdown is empty")

    if config.max_input_chars is not None and len(markdown_text) > config.max_input_chars:
        error = f"source markdown has {len(markdown_text)} chars, above max_input_chars={config.max_input_chars}"
        if config.fail_open:
            return MarkdownRefineResult(markdown_path=markdown_path, refined=False, error=error)
        raise ValueError(error)

    request = LLMRequest(
        feature=config.feature,
        messages=[
            LLMMessage(
                role="user",
                content=build_markdown_refine_request_content(
                    resolve_markdown_refine_instructions(config),
                    markdown_text,
                ),
            )
        ],
    )

    try:
        response = await llm_client.generate(request)
    except Exception as exc:
        if config.fail_open:
            return MarkdownRefineResult(markdown_path=markdown_path, refined=False, error=str(exc))
        raise

    refined_text = strip_markdown_fence(response.message.content)
    if not refined_text:
        error = "LLM returned empty markdown"
        if config.fail_open:
            return MarkdownRefineResult(markdown_path=markdown_path, refined=False, error=error)
        raise ValueError(error)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{refined_text.rstrip()}\n", encoding="utf-8")
    return MarkdownRefineResult(markdown_path=output_path, refined=True)


__all__ = [
    "LLMGenerateClient",
    "MarkdownRefineResult",
    "build_markdown_refine_request_content",
    "refine_markdown_with_llm",
    "resolve_markdown_refine_instructions",
    "strip_markdown_fence",
]
