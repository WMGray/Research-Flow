from __future__ import annotations

import os
import re
import shutil
import tempfile
from functools import lru_cache
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from backend.core.services.papers.utils import read_yaml, write_text


FRONTMATTER_KEYS = (
    "title",
    "authors",
    "venue",
    "year",
    "doi",
    "domain",
    "area",
    "topic",
    "tags",
    "updated_at",
)


@dataclass(frozen=True, slots=True)
class PdfParserResult:
    status: str
    parser: str
    refined_path: str
    image_dir: str
    text_path: str
    sections_path: str
    error: str = ""


def parse_pdf(paper_dir: Path, *, force: bool = False, parser: str = "auto") -> PdfParserResult:
    pdf_path = paper_dir / "paper.pdf"
    if not pdf_path.exists():
        return _result("needs-pdf", "mineru", paper_dir, f"PDF 不存在：{pdf_path}")

    if parser not in {"auto", "mineru"}:
        return _result("failed", "mineru", paper_dir, f"Unsupported parser: {parser}")

    return _parse_with_mineru(pdf_path, paper_dir, force=force)


def parser_health() -> dict[str, Any]:
    return {
        "mineru_sdk_available": _mineru_sdk_available(),
        "mineru_token_configured": bool(_first_env("RFLOW_MINERU_API_TOKEN", "MINERU__API_TOKEN", "MINERU_API_TOKEN")),
    }


def _parse_with_mineru(pdf_path: Path, paper_dir: Path, *, force: bool) -> PdfParserResult:
    _apply_proxy_env()
    refined_path = paper_dir / "refined.md"
    image_dir = paper_dir / "images"
    if _body_is_nonempty(refined_path) and not force:
        return PdfParserResult(
            status="skipped",
            parser="mineru",
            refined_path=str(refined_path),
            image_dir=str(image_dir),
            text_path=str(paper_dir / "parsed" / "text.md"),
            sections_path=str(paper_dir / "parsed" / "sections.json"),
            error="refined.md 已存在且正文非空；如需覆盖请使用 force。",
        )

    token = _first_env("RFLOW_MINERU_API_TOKEN", "MINERU__API_TOKEN", "MINERU_API_TOKEN")
    if not token:
        return _result("failed", "mineru", paper_dir, "未配置 MinerU token。")

    try:
        MinerU, exceptions = _load_mineru_sdk()
        base_url = _sdk_base_url(_first_env("RFLOW_MINERU_BASE_URL", "MINERU__BASE_URL", "MINERU_BASE_URL") or "https://mineru.net")
        model = _first_env("RFLOW_MINERU_MODEL", "MINERU__MODEL", "MINERU_MODEL") or "vlm"
        timeout = int(_first_env("RFLOW_MINERU_POLL_TIMEOUT_SECONDS", "MINERU__POLL_TIMEOUT_SECONDS") or "900")
        with tempfile.TemporaryDirectory(prefix="research-flow-mineru-") as tmp_name:
            artifact_dir = Path(tmp_name) / "artifacts"
            artifact_dir.mkdir(parents=True, exist_ok=True)
            client = MinerU(token=token, base_url=base_url)
            try:
                result = client.extract(str(pdf_path), model=model, formula=True, table=True, timeout=timeout)
            except exceptions["AuthError"] as error:
                raise RuntimeError("MinerU 认证失败，请检查 API Token。") from error
            except exceptions["TimeoutError"] as error:
                raise RuntimeError("等待 MinerU 返回解析结果超时。") from error
            except exceptions["MinerUError"] as error:
                raise RuntimeError(f"MinerU 解析失败：{error}") from error
            finally:
                close = getattr(client, "close", None)
                if callable(close):
                    close()
            _save_mineru_result(result, artifact_dir)
            markdown_path = artifact_dir / "full.md"
            if not markdown_path.exists():
                markdown_path.write_text(str(getattr(result, "markdown", "") or ""), encoding="utf-8")
            _write_refined(markdown_path, artifact_dir / "images", paper_dir)
        return _result("processed", "mineru", paper_dir, "")
    except Exception as error:  # noqa: BLE001
        return _result("failed", "mineru", paper_dir, str(error))


def _write_refined(markdown_path: Path, source_images: Path, paper_dir: Path) -> None:
    metadata = read_yaml(paper_dir / "metadata.yaml")
    target_images = paper_dir / "images"
    target_images.mkdir(parents=True, exist_ok=True)
    if source_images.exists():
        for source in source_images.iterdir():
            if source.is_file():
                shutil.copy2(source, target_images / source.name)
    raw_text = markdown_path.read_text(encoding="utf-8", errors="ignore")
    optimized = _optimize_markdown(raw_text, target_images)
    write_text(paper_dir / "refined.md", _with_frontmatter(optimized, metadata))


def _optimize_markdown(text: str, image_dir: Path) -> str:
    image_names = {item.name for item in image_dir.iterdir() if item.is_file()} if image_dir.exists() else set()
    lines: list[str] = []
    blank_seen = False
    for raw_line in text.replace("\r\n", "\n").split("\n"):
        line = _rewrite_image_links(_normalize_heading(raw_line.rstrip()), image_names)
        if not line.strip():
            if not blank_seen:
                lines.append("")
            blank_seen = True
            continue
        lines.append(line)
        blank_seen = False
    return "\n".join(lines).strip() + "\n"


def _normalize_heading(line: str) -> str:
    if not line.startswith("#"):
        return line
    text = line.lstrip("#").strip()
    known = {"abstract", "introduction", "related work", "method", "methods", "experiments", "results", "conclusion", "references"}
    if text.lower() in known:
        return f"## {text}"
    numbered = re.match(r"^(\d+(?:\.\d+)*)[\.\s]+(.+)$", text)
    if numbered:
        depth = min(numbered.group(1).count(".") + 2, 6)
        return f"{'#' * depth} {text}"
    return f"# {text}" if line.startswith("# ") else line


def _rewrite_image_links(line: str, image_names: set[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        alt = match.group("alt")
        target = match.group("target").strip()
        name = Path(target.replace("\\", "/")).name
        return f"![{alt}](images/{name})" if name in image_names else match.group(0)

    return re.sub(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)]+)\)", replace, line)


def _with_frontmatter(text: str, metadata: dict[str, Any]) -> str:
    return _render_frontmatter(metadata) + "\n" + _body(text).lstrip("\ufeff\n")


def _render_frontmatter(metadata: dict[str, Any]) -> str:
    lines = ["---"]
    for key in FRONTMATTER_KEYS:
        value = metadata.get(key)
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {_scalar_yaml(item)}" for item in value)
        elif value in (None, ""):
            lines.append(f"{key}:")
        else:
            lines.append(f"{key}: {_scalar_yaml(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _scalar_yaml(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_.:/+\\-]+", text):
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _body_is_nonempty(path: Path) -> bool:
    if not path.exists():
        return False
    return bool(_body(path.read_text(encoding="utf-8", errors="ignore")).strip())


def _body(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return text
    marker = normalized.find("\n---", 4)
    if marker < 0:
        return text
    body_start = marker + len("\n---")
    return normalized[body_start + 1 :] if normalized[body_start : body_start + 1] == "\n" else normalized[body_start:]


def _save_mineru_result(result: Any, artifact_dir: Path) -> None:
    image_dir = artifact_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    save_all = getattr(result, "save_all", None)
    if callable(save_all):
        try:
            save_all(str(artifact_dir))
            return
        except Exception:
            pass
    (artifact_dir / "full.md").write_text(str(getattr(result, "markdown", "") or ""), encoding="utf-8")
    for image in getattr(result, "images", []) or []:
        (image_dir / image.name).write_bytes(image.data)


def _load_mineru_sdk() -> tuple[Any, dict[str, Any]]:
    try:
        from mineru import AuthError, MinerU, MinerUError, TimeoutError
    except ModuleNotFoundError as error:
        raise RuntimeError("未安装 MinerU SDK。请先安装 mineru-open-sdk。") from error
    return MinerU, {"AuthError": AuthError, "TimeoutError": TimeoutError, "MinerUError": MinerUError}


def _result(status: str, parser: str, paper_dir: Path, error: str) -> PdfParserResult:
    return PdfParserResult(
        status=status,
        parser=parser,
        refined_path=str(paper_dir / "refined.md"),
        image_dir=str(paper_dir / "images"),
        text_path=str(paper_dir / "parsed" / "text.md"),
        sections_path=str(paper_dir / "parsed" / "sections.json"),
        error=error,
    )


def _sdk_base_url(base_url: str) -> str:
    clean = base_url.rstrip("/")
    return clean if clean.endswith("/api/v4") else f"{clean}/api/v4"


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    payload = _dotenv_payload()
    for name in names:
        value = payload.get(name)
        if value:
            return str(value)
    return None


@lru_cache(maxsize=1)
def _dotenv_payload() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return {}
    return {key: str(value) for key, value in dotenv_values(env_path).items() if key and value}


def _apply_proxy_env() -> None:
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy"):
        value = _first_env(name)
        if value and not os.environ.get(name):
            os.environ[name] = value


def _mineru_sdk_available() -> bool:
    try:
        _load_mineru_sdk()
    except RuntimeError:
        return False
    return True


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
