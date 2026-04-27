from __future__ import annotations

from pathlib import Path
import re

from core.config import backend_root


INSTRUCTION_KEY_ALIASES: dict[str, str] = {
    "paper_section_split.default": "paper_sectioning.default",
    "paper_extract_knowledge.default": "paper_knowledge_mining.default",
    "paper_extract_datasets.default": "paper_dataset_mining.default",
}
REFERENCE_FILE_OVERRIDES: dict[str, str] = {
    "paper_note_generate.block": "block-runtime-instructions.md",
}


def skills_root() -> Path:
    return backend_root().parent / "skills"


def load_skill_runtime_instructions(instruction_key: str) -> str:
    normalized_key = INSTRUCTION_KEY_ALIASES.get(instruction_key, instruction_key)
    skill_key, stage = _split_instruction_key(normalized_key)
    skill_name = skill_key.replace("_", "-")
    reference_file = REFERENCE_FILE_OVERRIDES.get(normalized_key, "runtime-instructions.md")
    instructions_path = skills_root() / skill_name / "references" / reference_file
    if not instructions_path.exists():
        raise KeyError(f"Paper skill runtime instructions not found: {instruction_key}")

    instructions = instructions_path.read_text(encoding="utf-8-sig")
    if not _has_stage_sections(instructions):
        return instructions
    return _extract_stage_section(instructions, stage, instruction_key)


def _split_instruction_key(instruction_key: str) -> tuple[str, str]:
    skill_key, separator, stage = instruction_key.partition(".")
    if not skill_key or not separator or not stage:
        raise KeyError(f"Invalid paper skill runtime instruction key: {instruction_key}")
    return skill_key, stage


def _has_stage_sections(instructions: str) -> bool:
    return bool(re.search(r"(?m)^<!--\s*stage:[a-zA-Z0-9_-]+\s*-->\s*$", instructions))


def _extract_stage_section(instructions: str, section: str, instruction_key: str) -> str:
    pattern = re.compile(
        rf"(?ms)^<!--\s*stage:{re.escape(section)}\s*-->\s*(.*?)\s*^<!--\s*/stage\s*-->\s*$"
    )
    match = pattern.search(instructions)
    if match is None:
        raise KeyError(f"Paper skill runtime instruction stage not found: {instruction_key}#{section}")
    return match.group(1).strip() + "\n"


def render_skill_instructions(instructions: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        instructions = instructions.replace(f"{{{{{key}}}}}", value)
        instructions = instructions.replace(f"{{{key}}}", value)
    return instructions


__all__ = [
    "REFERENCE_FILE_OVERRIDES",
    "INSTRUCTION_KEY_ALIASES",
    "skills_root",
    "load_skill_runtime_instructions",
    "render_skill_instructions",
]
