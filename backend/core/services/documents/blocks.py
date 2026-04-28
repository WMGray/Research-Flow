"""Shared helpers for RF managed Markdown blocks."""

from __future__ import annotations

from dataclasses import dataclass
import re


RF_BLOCK_RE = re.compile(
    r'<!-- RF:BLOCK_START id="(?P<id>[^"]+)" '
    r'managed="(?P<managed>true|false)" version="(?P<version>[^"]+)" -->'
    r".*?"
    r'<!-- RF:BLOCK_END id="(?P=id)" -->',
    re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class RFBlock:
    block_id: str
    managed: bool
    version: str
    markdown: str


def render_managed_block(
    *,
    block_id: str,
    title: str,
    content: str,
    version: int = 1,
) -> str:
    body = content.strip() or "Pending synthesis."
    return "\n".join(
        [
            f'<!-- RF:BLOCK_START id="{block_id}" managed="true" version="{version}" -->',
            f"## {title}",
            "",
            body,
            f'<!-- RF:BLOCK_END id="{block_id}" -->',
        ]
    )


def extract_rf_blocks(markdown: str) -> dict[str, RFBlock]:
    blocks: dict[str, RFBlock] = {}
    for match in RF_BLOCK_RE.finditer(markdown):
        block_id = str(match.group("id"))
        blocks[block_id] = RFBlock(
            block_id=block_id,
            managed=str(match.group("managed")) == "true",
            version=str(match.group("version")),
            markdown=match.group(0).strip(),
        )
    return blocks


def extract_managed_blocks(markdown: str) -> dict[str, str]:
    return {
        block_id: block.markdown
        for block_id, block in extract_rf_blocks(markdown).items()
        if block.managed
    }


def merge_managed_blocks(
    *,
    existing: str,
    generated: str,
    block_order: list[str] | tuple[str, ...],
    skip_locked_blocks: bool = True,
    deprecated_ids: set[str] | frozenset[str] = frozenset(),
) -> str:
    """Replace generated RF blocks while preserving free-form text."""

    if not existing.strip():
        return generated.rstrip() + "\n"

    generated_blocks = extract_managed_blocks(generated)
    if not generated_blocks:
        return existing.rstrip() + "\n"

    merged = _remove_blocks(existing.rstrip(), deprecated_ids)
    existing_blocks = extract_rf_blocks(merged)
    missing_blocks: list[str] = []
    ordered_ids = [*block_order, *sorted(set(generated_blocks) - set(block_order))]
    for block_id in ordered_ids:
        replacement = generated_blocks.get(block_id)
        if replacement is None:
            continue
        existing_block = existing_blocks.get(block_id)
        if existing_block is not None and not existing_block.managed and skip_locked_blocks:
            continue
        merged, replace_count = _replace_block(merged, block_id, replacement)
        if replace_count == 0:
            missing_blocks.append(replacement)

    if missing_blocks:
        merged = merged.rstrip() + "\n\n" + "\n\n".join(missing_blocks)
    return merged.rstrip() + "\n"


def _replace_block(markdown: str, block_id: str, replacement: str) -> tuple[str, int]:
    block_pattern = re.compile(
        rf'<!-- RF:BLOCK_START id="{re.escape(block_id)}" '
        rf'managed="(?:true|false)" version="[^"]+" -->.*?'
        rf'<!-- RF:BLOCK_END id="{re.escape(block_id)}" -->',
        re.DOTALL,
    )
    return block_pattern.subn(replacement, markdown, count=1)


def _remove_blocks(markdown: str, block_ids: set[str] | frozenset[str]) -> str:
    cleaned = markdown
    for block_id in block_ids:
        block_pattern = re.compile(
            rf'\n*<!-- RF:BLOCK_START id="{re.escape(block_id)}" '
            rf'managed="(?:true|false)" version="[^"]+" -->.*?'
            rf'<!-- RF:BLOCK_END id="{re.escape(block_id)}" -->\n*',
            re.DOTALL,
        )
        cleaned = block_pattern.sub("\n\n", cleaned)
    return cleaned.rstrip()
