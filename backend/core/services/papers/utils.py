from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(read_text(path))
    return data if isinstance(data, dict) else {}


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            data,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ),
        encoding="utf-8",
        newline="\n",
    )


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def slugify(value: str, fallback: str = "paper") -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or fallback


def unique_list(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    result: list[Any] = []
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}, text
    try:
        _, remainder = normalized.split("---\n", 1)
        header, body = remainder.split("\n---\n", 1)
    except ValueError:
        return {}, text
    data = yaml.safe_load(header)
    return (data if isinstance(data, dict) else {}), body


def load_markdown_front_matter(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    front_matter, _ = split_front_matter(read_text(path))
    return front_matter


def merge_metadata(*sources: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for source in sources:
        for key, value in source.items():
            if value in (None, "", [], {}):
                continue
            if key == "tags":
                current = list(result.get("tags", []))
                if isinstance(value, list):
                    current.extend(value)
                elif isinstance(value, str):
                    current.append(value)
                else:
                    current.append(str(value))
                result["tags"] = unique_list(current)
                continue
            result[key] = value
    if "tags" not in result:
        result["tags"] = ["paper"]
    return result
