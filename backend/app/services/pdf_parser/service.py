from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
import re
import shutil
from urllib.parse import quote
import zipfile

import httpx

from app.core.config import Settings
from app.core.mineru_config import MinerUConfig
from app.services.pdf_parser.postprocess import ProcessedMarkdownArtifacts, process_mineru_markdown_artifacts


SECTION_PATTERNS: list[tuple[str, str, tuple[str, ...]]] = [
    ("abstract", "Abstract", ("abstract", "summary")),
    ("introduction", "Introduction", ("introduction", "overview", "background")),
    ("related_work", "Related Work", ("related work", "prior work", "literature review")),
    ("methodology", "Method", ("method", "methods", "methodology", "approach", "model", "proposed method")),
    ("experiments", "Experiments", ("experiment", "experiments", "evaluation", "results", "experimental setup")),
    ("discussion", "Discussion", ("discussion", "analysis", "ablation study")),
    ("conclusion", "Conclusion", ("conclusion", "conclusions", "future work")),
    ("references", "References", ("references", "bibliography")),
    ("appendix", "Appendix", ("appendix", "supplementary material")),
]

NON_CONTEXT_SECTION_KEYS = {"references", "appendix"}
SECTION_CONTEXT_PRIORITY = ["abstract", "introduction", "methodology", "experiments", "discussion", "conclusion"]

ParserProgressCallback = Callable[[str, str], Awaitable[None] | None]


class PDFParserError(RuntimeError):
    """PDF 解析阶段的业务异常，保留状态码和错误码便于后续接 API。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 500,
        error_code: str = "PDF_PARSE_ERROR",
        raw_error_detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.raw_error_detail = raw_error_detail


@dataclass(slots=True)
class ParsedPaperSection:
    key: str
    title: str
    text: str
    char_count: int


@dataclass(slots=True)
class ParsedPaperContent:
    text: str
    page_count: int
    char_count: int
    excerpt: str
    sections: list[ParsedPaperSection] = field(default_factory=list)
    artifact_markdown_path: Path | None = None
    artifact_image_dir: Path | None = None

    def section_outline(self) -> list[dict[str, object]]:
        return [
            {
                "key": section.key,
                "title": section.title,
                "char_count": section.char_count,
            }
            for section in self.sections
        ]


@dataclass(slots=True)
class MinerUExtractionResult:
    markdown_text: str
    markdown_path: Path
    image_dir: Path
    page_count: int
    content_list_path: Path | None = None


class PDFParserService:
    """通过 MinerU 解析 PDF，并把 Markdown 结果整理成后续 LLM 可用的文本。"""

    def __init__(self, settings: Settings | MinerUConfig) -> None:
        self.config = settings.mineru if isinstance(settings, Settings) else settings

    async def parse_pdf(
        self,
        pdf_path: Path,
        *,
        artifact_dir: Path | None = None,
        progress_callback: ParserProgressCallback | None = None,
    ) -> ParsedPaperContent:
        if not pdf_path.exists():
            raise PDFParserError("PDF 文件不存在。", status_code=404, error_code="PDF_NOT_FOUND")
        if not self.config.api_token:
            raise PDFParserError("未配置 MinerU API Token，无法解析 PDF。", status_code=500, error_code="MINERU_TOKEN_MISSING")

        # MinerU 会返回一个 ZIP 结果包；这里将结果固定落到 PDF 旁边的 mineru 目录，方便后续复用。
        artifact_dir = artifact_dir or (pdf_path.parent / "mineru")
        bundle = await self._extract_with_mineru(
            pdf_path=pdf_path,
            artifact_dir=artifact_dir,
            progress_callback=progress_callback,
        )
        artifact_markdown_path = bundle.markdown_path
        artifact_image_dir = bundle.image_dir
        processed_artifacts = await self._postprocess_mineru_artifacts(
            pdf_path=pdf_path,
            bundle=bundle,
            progress_callback=progress_callback,
        )
        if processed_artifacts is not None:
            artifact_markdown_path = processed_artifacts.markdown_path
            artifact_image_dir = processed_artifacts.figure_dir
        await self._emit(progress_callback, "PDF_PARSING_NORMALIZE", "正在整理 MinerU 返回的 Markdown 结果。")
        full_text, sections = self._parse_markdown(bundle.markdown_text)
        if len(full_text) < self.config.pdf_parse_min_chars:
            raise PDFParserError("解析出的 PDF 正文过短，无法继续后续分析。", status_code=422, error_code="PDF_TEXT_TOO_SHORT")

        return ParsedPaperContent(
            text=full_text,
            page_count=max(1, bundle.page_count),
            char_count=len(full_text),
            excerpt=full_text[: self.config.pdf_parse_excerpt_chars],
            sections=sections,
            artifact_markdown_path=artifact_markdown_path,
            artifact_image_dir=artifact_image_dir,
        )

    async def parse_existing_markdown(
        self,
        markdown_path: Path,
        *,
        image_dir: Path | None = None,
    ) -> ParsedPaperContent:
        if not markdown_path.exists():
            raise PDFParserError("本地 MinerU Markdown 不存在。", status_code=404, error_code="LOCAL_MARKDOWN_NOT_FOUND")
        markdown_text = markdown_path.read_text(encoding="utf-8")
        full_text, sections = self._parse_markdown(markdown_text)
        if len(full_text) < self.config.pdf_parse_min_chars:
            raise PDFParserError("本地 MinerU Markdown 正文过短。", status_code=422, error_code="LOCAL_MARKDOWN_TOO_SHORT")
        return ParsedPaperContent(
            text=full_text,
            page_count=max(1, markdown_text.count("[Page ")),
            char_count=len(full_text),
            excerpt=full_text[: self.config.pdf_parse_excerpt_chars],
            sections=sections,
            artifact_markdown_path=markdown_path,
            artifact_image_dir=image_dir if image_dir and image_dir.exists() else None,
        )

    async def parse_existing_text(self, text_path: Path) -> ParsedPaperContent:
        if not text_path.exists():
            raise PDFParserError("本地解析文本不存在。", status_code=404, error_code="LOCAL_PARSED_TEXT_NOT_FOUND")
        text = text_path.read_text(encoding="utf-8").strip()
        if len(text) < self.config.pdf_parse_min_chars:
            raise PDFParserError("本地解析文本过短。", status_code=422, error_code="LOCAL_PARSED_TEXT_TOO_SHORT")
        return ParsedPaperContent(
            text=text,
            page_count=max(1, text.count("[Page ")),
            char_count=len(text),
            excerpt=text[: self.config.pdf_parse_excerpt_chars],
            sections=[],
            artifact_markdown_path=text_path if text_path.suffix.lower() == ".md" else None,
            artifact_image_dir=None,
        )

    def build_llm_context(self, parsed_content: ParsedPaperContent) -> str:
        if parsed_content.sections:
            section_context = self._build_section_context(parsed_content.sections)
            if section_context:
                return section_context
        return self._build_fallback_context(parsed_content.text)

    async def _extract_with_mineru(
        self,
        *,
        pdf_path: Path,
        artifact_dir: Path,
        progress_callback: ParserProgressCallback | None,
    ) -> MinerUExtractionResult:
        artifact_dir.mkdir(parents=True, exist_ok=True)

        headers = {"Authorization": f"Bearer {self.config.api_token}"}
        timeout = httpx.Timeout(self.config.http_timeout_seconds, connect=30.0)
        base_url = self.config.base_url.rstrip("/")

        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. 创建批量文件解析任务，MinerU 返回 batch_id 和预签名上传地址。
            await self._emit(progress_callback, "PDF_PARSING_CREATE_JOB", "正在创建 MinerU 解析任务。")
            create_response = await self._create_mineru_job(client, base_url, headers, pdf_path)
            create_payload = self._json_response(create_response, "MINERU_CREATE_RESPONSE_INVALID", "MinerU 创建任务接口返回的不是合法 JSON。")
            if create_payload.get("code") != 0:
                raise PDFParserError("MinerU 拒绝了本次解析任务。", status_code=502, error_code="MINERU_CREATE_REJECTED")

            data = create_payload.get("data") or {}
            batch_id = data.get("batch_id")
            upload_url = (data.get("file_urls") or [None])[0]
            if not batch_id or not upload_url:
                raise PDFParserError("MinerU 创建任务返回缺少 batch_id 或上传地址。", status_code=502, error_code="MINERU_CREATE_RESPONSE_INCOMPLETE")

            # 2. 将本地 PDF 上传到预签名地址，上传地址通常不是 MinerU 主域名。
            await self._emit(progress_callback, "PDF_PARSING_UPLOAD", "正在上传 PDF 到 MinerU。")
            await self._upload_pdf(client, upload_url, pdf_path)

            # 3. 轮询 batch_id，直到 MinerU 解析完成并返回结果包下载地址。
            await self._emit(progress_callback, "PDF_PARSING_WAITING", "正在等待 MinerU 返回解析结果。")
            result = await self._poll_mineru_result(
                client=client,
                base_url=base_url,
                headers=headers,
                batch_id=batch_id,
                progress_callback=progress_callback,
            )

            zip_url = result.get("full_zip_url")
            if not zip_url:
                raise PDFParserError("MinerU 没有返回结果包下载地址。", status_code=502, error_code="MINERU_ZIP_URL_MISSING")

            # 4. 下载 ZIP 结果包，落地 full.md 和 images，后续重跑可直接读取本地文件。
            await self._emit(progress_callback, "PDF_PARSING_DOWNLOAD", "正在下载 MinerU 结果包。")
            zip_response = await self._download_bundle(client, str(zip_url))

        try:
            markdown_path, image_dir, content_list_path = self._extract_zip_bundle(zip_response.content, artifact_dir)
        except zipfile.BadZipFile as exc:
            raise PDFParserError("MinerU 返回的结果包不是合法的 ZIP 文件。", status_code=502, error_code="MINERU_BUNDLE_INVALID") from exc
        except OSError as exc:
            raise PDFParserError("写入 MinerU 结果包到本地文件夹失败。", status_code=500, error_code="MINERU_BUNDLE_WRITE_FAILED") from exc

        try:
            markdown_text = markdown_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise PDFParserError("MinerU 返回的 Markdown 文件编码无法解析。", status_code=502, error_code="MINERU_MARKDOWN_DECODE_FAILED") from exc
        except OSError as exc:
            raise PDFParserError("读取 MinerU 返回的 Markdown 文件失败。", status_code=500, error_code="MINERU_MARKDOWN_READ_FAILED") from exc
        return MinerUExtractionResult(
            markdown_text=markdown_text,
            markdown_path=markdown_path,
            image_dir=image_dir,
            page_count=self._page_count_from_result(result),
            content_list_path=content_list_path,
        )

    async def _create_mineru_job(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        headers: dict[str, str],
        pdf_path: Path,
    ) -> httpx.Response:
        try:
            response = await self._request_with_retries(
                client,
                "POST",
                f"{base_url}/api/v4/file-urls/batch",
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "files": [{"name": pdf_path.name, "data_id": pdf_path.stem}],
                    "model_version": self.config.model,
                    "enable_formula": True,
                    "enable_table": True,
                },
            )
            response.raise_for_status()
            return response
        except httpx.RequestError as exc:
            raise self._network_error("创建 MinerU 解析任务时网络连接失败。", "MINERU_CREATE_JOB_CONNECT_ERROR", exc) from exc
        except httpx.HTTPError as exc:
            raise PDFParserError("创建 MinerU 解析任务失败。", status_code=502, error_code="MINERU_CREATE_JOB_FAILED") from exc

    async def _upload_pdf(self, client: httpx.AsyncClient, upload_url: str, pdf_path: Path) -> None:
        try:
            response = await self._request_with_retries(client, "PUT", upload_url, content=pdf_path.read_bytes())
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise self._network_error("上传 PDF 到 MinerU 时网络连接失败。", "MINERU_UPLOAD_CONNECT_ERROR", exc) from exc
        except httpx.HTTPError as exc:
            raise PDFParserError("上传 PDF 到 MinerU 失败。", status_code=502, error_code="MINERU_UPLOAD_FAILED") from exc

    async def _download_bundle(self, client: httpx.AsyncClient, zip_url: str) -> httpx.Response:
        candidate_urls = [zip_url]
        cdn_prefix = "https://cdn-mineru.openxlab.org.cn"
        oss_prefix = "https://mineru.oss-cn-shanghai.aliyuncs.com"
        if zip_url.startswith(cdn_prefix):
            candidate_urls.append(zip_url.replace(cdn_prefix, oss_prefix, 1))

        last_error: Exception | None = None
        for candidate_url in candidate_urls:
            try:
                response = await self._request_with_retries(client, "GET", candidate_url)
                response.raise_for_status()
                return response
            except (httpx.RequestError, httpx.HTTPError) as exc:
                last_error = exc

        if isinstance(last_error, httpx.RequestError):
            raise self._network_error("下载 MinerU 结果包时网络连接失败。", "MINERU_ZIP_DOWNLOAD_CONNECT_ERROR", last_error) from last_error
        if isinstance(last_error, httpx.HTTPError):
            raise PDFParserError("下载 MinerU 结果包失败。", status_code=502, error_code="MINERU_ZIP_DOWNLOAD_FAILED") from last_error
        raise PDFParserError("下载 MinerU 结果包失败。", status_code=502, error_code="MINERU_ZIP_DOWNLOAD_FAILED")

    async def _poll_mineru_result(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str,
        headers: dict[str, str],
        batch_id: str,
        progress_callback: ParserProgressCallback | None,
    ) -> dict[str, object]:
        deadline = asyncio.get_running_loop().time() + self.config.poll_timeout_seconds
        last_state: str | None = None

        while asyncio.get_running_loop().time() < deadline:
            try:
                query_response = await self._request_with_retries(
                    client,
                    "GET",
                    f"{base_url}/api/v4/extract-results/batch/{quote(batch_id)}",
                    headers=headers,
                )
                query_response.raise_for_status()
            except httpx.RequestError as exc:
                raise self._network_error("查询 MinerU 解析状态时网络连接失败。", "MINERU_STATUS_CONNECT_ERROR", exc) from exc
            except httpx.HTTPError as exc:
                raise PDFParserError("查询 MinerU 解析状态失败。", status_code=502, error_code="MINERU_STATUS_REQUEST_FAILED") from exc

            query_payload = self._json_response(query_response, "MINERU_STATUS_RESPONSE_INVALID", "MinerU 状态接口返回的不是合法 JSON。")
            if query_payload.get("code") != 0:
                raise PDFParserError("MinerU 状态轮询返回失败。", status_code=502, error_code="MINERU_STATUS_POLL_FAILED")

            result = self._pick_result(query_payload)
            state = str(result.get("state") or "").lower()
            if state != last_state:
                await self._emit(progress_callback, "PDF_PARSING_WAITING", f"MinerU 当前状态：{state or 'unknown'}。")
                last_state = state
            if state == "done":
                return result
            if state == "failed":
                err_msg = result.get("err_msg") or "服务端未返回更多原因。"
                raise PDFParserError(f"MinerU 解析失败：{err_msg}", status_code=502, error_code="MINERU_STATE_FAILED")
            await asyncio.sleep(self.config.poll_interval_seconds)

        raise PDFParserError("等待 MinerU 返回解析结果超时。", status_code=504, error_code="MINERU_TIMEOUT")

    def _extract_zip_bundle(self, zip_bytes: bytes, output_dir: Path) -> tuple[Path, Path, Path | None]:
        markdown_path = output_dir / "full.md"
        image_dir = output_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        content_list_path: Path | None = None

        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as archive:
            for item in archive.infolist():
                inner_path = Path(item.filename)
                if item.is_dir():
                    continue
                if inner_path.name == "full.md":
                    with archive.open(item) as src, markdown_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    continue
                if "images" in inner_path.parts:
                    target_path = image_dir / inner_path.name
                    with archive.open(item) as src, target_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    continue
                if inner_path.name == "content_list_v2.json":
                    content_list_path = output_dir / "content_list_v2.json"
                    with archive.open(item) as src, content_list_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    continue
                if inner_path.name == "layout.json":
                    target_path = output_dir / "layout.json"
                    with archive.open(item) as src, target_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst)

        if not markdown_path.exists():
            raise PDFParserError("MinerU 结果包中缺少 full.md。", status_code=502, error_code="MINERU_MARKDOWN_MISSING")
        return markdown_path, image_dir, content_list_path

    async def _postprocess_mineru_artifacts(
        self,
        *,
        pdf_path: Path,
        bundle: MinerUExtractionResult,
        progress_callback: ParserProgressCallback | None,
    ) -> ProcessedMarkdownArtifacts | None:
        if bundle.content_list_path is None or not bundle.content_list_path.exists():
            return None
        await self._emit(progress_callback, "PDF_PARSING_FIGURES", "正在合并 MinerU 提取图片并重写 Markdown 引用。")
        try:
            return process_mineru_markdown_artifacts(
                raw_markdown_path=bundle.markdown_path,
                source_image_dir=bundle.image_dir,
                content_list_path=bundle.content_list_path,
                output_markdown_path=pdf_path.parent / "LLM.md",
                output_figure_dir=pdf_path.parent / "figures",
            )
        except Exception:
            return None

    def _parse_markdown(self, markdown_text: str) -> tuple[str, list[ParsedPaperSection]]:
        sections: list[ParsedPaperSection] = []
        current_title = "Main Body"
        current_key = "main_body"
        current_lines: list[str] = []

        for raw_line in markdown_text.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                if current_lines and current_lines[-1] != "":
                    current_lines.append("")
                continue

            heading = self._match_markdown_heading(stripped)
            if heading is not None:
                section = self._flush_section(current_key, current_title, current_lines)
                if section is not None:
                    sections.append(section)
                current_key, current_title = heading
                current_lines = []
                continue

            normalized = self._normalize_markdown_line(stripped)
            if normalized:
                current_lines.append(normalized)

        section = self._flush_section(current_key, current_title, current_lines)
        if section is not None:
            sections.append(section)

        merged_sections = self._merge_small_sections(sections)
        full_text = "\n\n".join(section.text for section in merged_sections).strip()
        return full_text, merged_sections

    def _build_section_context(self, sections: list[ParsedPaperSection]) -> str:
        available_chars = self.config.llm_pdf_context_chars
        blocks: list[str] = []

        prioritized_sections = [section for key in SECTION_CONTEXT_PRIORITY for section in sections if section.key == key]
        fallback_sections = [
            section
            for section in sections
            if section.key not in NON_CONTEXT_SECTION_KEYS and section.key not in SECTION_CONTEXT_PRIORITY
        ]

        for section in prioritized_sections + fallback_sections:
            if available_chars <= 200:
                break

            max_section_chars = min(self.config.llm_pdf_section_chars, available_chars)
            clipped_text = self._clip_text(section.text, max_section_chars)
            if not clipped_text:
                continue

            block = f"[Section: {section.title}]\n{clipped_text}"
            blocks.append(block)
            available_chars -= len(block) + 2

        return "\n\n".join(blocks).strip()

    def _build_fallback_context(self, text: str) -> str:
        text = text.strip()
        if len(text) <= self.config.llm_pdf_context_chars:
            return text

        head_chars = int(self.config.llm_pdf_context_chars * 0.7)
        tail_chars = self.config.llm_pdf_context_chars - head_chars
        head = text[:head_chars].rstrip()
        tail = text[-tail_chars:].lstrip()
        return f"{head}\n\n[... truncated ...]\n\n{tail}"

    def _match_markdown_heading(self, line: str) -> tuple[str, str] | None:
        if not line.startswith("#"):
            return None

        candidate = self._normalize_heading(line.lstrip("#").strip())
        if not candidate:
            return None
        for key, title, aliases in SECTION_PATTERNS:
            if candidate in aliases:
                return key, title
        return None

    def _normalize_heading(self, line: str) -> str:
        candidate = line.lower().strip()
        candidate = re.sub(r"^(section\s+)?([ivxlcdm]+|\d+)(\.\d+)*[\)\.\-: ]+", "", candidate)
        candidate = candidate.strip(" .:-#")
        candidate = re.sub(r"\s+", " ", candidate)

        if len(candidate) < 3 or len(candidate) > 60:
            return ""
        if len(candidate.split()) > 5:
            return ""
        if not re.fullmatch(r"[a-z][a-z0-9 /&-]*", candidate):
            return ""
        return candidate

    def _flush_section(self, key: str, title: str, lines: list[str]) -> ParsedPaperSection | None:
        text = "\n".join(lines).strip()
        if not text:
            return None
        return ParsedPaperSection(key=key, title=title, text=text, char_count=len(text))

    def _merge_small_sections(self, sections: list[ParsedPaperSection]) -> list[ParsedPaperSection]:
        if not sections:
            return []

        merged: list[ParsedPaperSection] = []
        for section in sections:
            if (
                merged
                and section.char_count < 120
                and section.key not in SECTION_CONTEXT_PRIORITY
                and merged[-1].key == "main_body"
            ):
                merged[-1].text = f"{merged[-1].text}\n\n[{section.title}]\n{section.text}".strip()
                merged[-1].char_count = len(merged[-1].text)
                continue
            merged.append(section)
        return merged

    def _normalize_markdown_line(self, line: str) -> str:
        line = re.sub(r"!\[[^\]]*]\([^)]*\)", "", line)
        line = re.sub(r"\[([^\]]+)]\([^)]*\)", r"\1", line)
        line = re.sub(r"`{1,3}", "", line)
        line = re.sub(r"^[-*+]\s+", "", line)
        line = re.sub(r"^\d+\.\s+", "", line)
        line = re.sub(r"<[^>]+>", " ", line)
        line = line.replace("|", " ")
        line = " ".join(line.split())
        return line.strip()

    def _page_count_from_result(self, result: dict[str, object]) -> int:
        for key in ("page_count", "page_num", "pages"):
            value = result.get(key)
            if isinstance(value, int) and value > 0:
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
        return 1

    def _pick_result(self, payload: dict[str, object]) -> dict[str, object]:
        data = payload.get("data", {})
        if not isinstance(data, dict):
            raise PDFParserError("MinerU 返回的数据格式不正确。", status_code=502, error_code="MINERU_RESPONSE_INVALID")

        result = data.get("extract_result")
        if isinstance(result, dict):
            return result
        if isinstance(result, list) and result and isinstance(result[0], dict):
            return result[0]
        raise PDFParserError("MinerU 返回结果中缺少 extract_result。", status_code=502, error_code="MINERU_RESULT_MISSING")

    async def _emit(
        self,
        progress_callback: ParserProgressCallback | None,
        step: str,
        message: str,
    ) -> None:
        if progress_callback is None:
            return
        result = progress_callback(step, message)
        if isinstance(result, Awaitable):
            await result

    async def _request_with_retries(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        last_exc: httpx.RequestError | None = None
        for attempt in range(3):
            try:
                return await client.request(method, url, **kwargs)
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt == 2:
                    raise
                await asyncio.sleep(0.6 * (2**attempt))
        assert last_exc is not None
        raise last_exc

    @staticmethod
    def _json_response(response: httpx.Response, error_code: str, message: str) -> dict[str, object]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise PDFParserError(message, status_code=502, error_code=error_code) from exc
        if not isinstance(payload, dict):
            raise PDFParserError(message, status_code=502, error_code=error_code)
        return payload

    @staticmethod
    def _network_error(message: str, error_code: str, exc: httpx.RequestError) -> PDFParserError:
        detail = f"{type(exc).__name__}: {exc}"
        return PDFParserError(
            message,
            status_code=502,
            error_code=error_code,
            raw_error_detail=detail[:4000],
        )

    @staticmethod
    def _clip_text(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        clipped = text[: max_chars - 18].rstrip()
        return f"{clipped}\n[... truncated ...]"
