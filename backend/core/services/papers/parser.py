from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.services.papers.utils import read_yaml, write_json, write_text


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
        return _result("needs-pdf", parser, paper_dir, f"PDF 不存在：{pdf_path}")

    if parser in {"auto", "mineru"}:
        mineru_result = _parse_with_mineru(pdf_path, paper_dir, force=force)
        if mineru_result.status == "processed" or parser == "mineru":
            return mineru_result

    return _parse_with_pymupdf(pdf_path, paper_dir, force=force, prior_error="")


def parser_health() -> dict[str, Any]:
    return {
        "mineru_sdk_available": _mineru_sdk_available(),
        "mineru_token_configured": bool(_first_env("RFLOW_MINERU_API_TOKEN", "MINERU__API_TOKEN", "MINERU_API_TOKEN")),
        "pymupdf_available": _pymupdf_available(),
    }


def _parse_with_mineru(pdf_path: Path, paper_dir: Path, *, force: bool) -> PdfParserResult:
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
        return _write_pending(paper_dir, "未配置 MinerU token，转入本地解析兜底。")

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
    except Exception as error:  # noqa: BLE001 - parser 失败必须回写到状态。
        _write_pending(paper_dir, str(error))
        return PdfParserResult(
            status="failed",
            parser="mineru",
            refined_path=str(refined_path),
            image_dir=str(image_dir),
            text_path=str(paper_dir / "parsed" / "text.md"),
            sections_path=str(paper_dir / "parsed" / "sections.json"),
            error=str(error),
        )


def _parse_with_pymupdf(pdf_path: Path, paper_dir: Path, *, force: bool, prior_error: str) -> PdfParserResult:
    try:
        import fitz
    except ModuleNotFoundError as error:
        return _result("failed", "pymupdf", paper_dir, f"未安装 PyMuPDF：{error}")

    parsed_dir = paper_dir / "parsed"
    text_path = parsed_dir / "text.md"
    sections_path = parsed_dir / "sections.json"
    analysis_path = paper_dir / "pdf_analysis.json"
    if text_path.exists() and sections_path.exists() and not force:
        return PdfParserResult("skipped", "pymupdf", str(paper_dir / "refined.md"), str(paper_dir / "images"), str(text_path), str(sections_path), "")

    try:
        parsed_dir.mkdir(parents=True, exist_ok=True)
        sections: list[dict[str, Any]] = []
        text_parts: list[str] = []
        with fitz.open(pdf_path) as document:
            for page_index, page in enumerate(document, start=1):
                text = page.get_text("text").strip()
                text_parts.append(f"\n\n## Page {page_index}\n\n{text}" if text else f"\n\n## Page {page_index}\n")
                sections.extend(_section_candidates(page_index, text))
        body = "# Parsed PDF Text\n" + "".join(text_parts).strip() + "\n"
        write_text(text_path, body)
        write_json(sections_path, {"sections": sections})
        write_json(
            analysis_path,
            {
                "parser": "pymupdf",
                "status": "processed",
                "text_path": str(text_path),
                "sections_path": str(sections_path),
                "prior_error": prior_error,
                "updated_at": _now_utc(),
            },
        )
        return PdfParserResult("processed", "pymupdf", str(paper_dir / "refined.md"), str(paper_dir / "images"), str(text_path), str(sections_path), "")
    except Exception as error:  # noqa: BLE001 - PDF 损坏等情况要返回给前端。
        return _result("failed", "pymupdf", paper_dir, str(error))


def _section_candidates(page_index: int, text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        is_numbered = bool(re.match(r"^\d+(?:\.\d+)*\s+[A-Z]", candidate))
        is_known = candidate.lower() in {"abstract", "introduction", "related work", "method", "methods", "experiments", "results", "conclusion", "references"}
        if is_numbered or is_known:
            sections.append({"page": page_index, "title": candidate[:180]})
    return sections


def _write_pending(paper_dir: Path, error: str) -> PdfParserResult:
    metadata = read_yaml(paper_dir / "metadata.yaml")
    refined_path = paper_dir / "refined.md"
    image_dir = paper_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    if not refined_path.exists() or not _body_is_nonempty(refined_path):
        write_text(refined_path, _render_frontmatter(metadata) + "\n")
    return _result("pending", "mineru", paper_dir, error)


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
    if re.fullmatch(r"[A-Za-z0-9_.:/+\-]+", text):
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
    return None


def _mineru_sdk_available() -> bool:
    try:
        _load_mineru_sdk()
    except RuntimeError:
        return False
    return True


def _pymupdf_available() -> bool:
    try:
        import fitz  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
