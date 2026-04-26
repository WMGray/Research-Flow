from __future__ import annotations

from pathlib import Path
import re
import tomllib

from core.config import backend_root


def config_root() -> Path:
    return backend_root() / "config"


def load_toml_config(filename: str) -> dict[str, object]:
    with (config_root() / filename).open("rb") as handle:
        return tomllib.load(handle)


def load_prompt_template(template_key: str) -> str:
    prompt_templates = load_toml_config("prompt_templates.toml")
    record = prompt_templates.get(template_key)
    if not isinstance(record, dict):
        raise KeyError(f"Unknown prompt template: {template_key}")
    relative_path = str(record.get("path") or "").strip()
    if not relative_path:
        raise ValueError(f"Prompt template path is empty: {template_key}")
    template_text = (config_root() / relative_path).read_text(encoding="utf-8")
    section = str(record.get("section") or "").strip()
    if not section:
        return template_text
    return _extract_prompt_section(template_text, section, template_key)


def _extract_prompt_section(template_text: str, section: str, template_key: str) -> str:
    pattern = re.compile(
        rf"(?ms)^<!--\s*prompt:{re.escape(section)}\s*-->\s*(.*?)\s*^<!--\s*/prompt\s*-->\s*$"
    )
    match = pattern.search(template_text)
    if match is None:
        raise KeyError(f"Prompt section not found: {template_key}#{section}")
    return match.group(1).strip() + "\n"


def render_template(template_text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template_text = template_text.replace(f"{{{{{key}}}}}", value)
        template_text = template_text.replace(f"{{{key}}}", value)
    return template_text


__all__ = ["config_root", "load_prompt_template", "load_toml_config", "render_template"]
