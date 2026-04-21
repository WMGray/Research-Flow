from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
import shutil
from urllib.parse import quote
import zipfile

import httpx

from app.core.config import Settings
from app.core.mineru_config import MinerUConfig
from app.services.pdf_parser.postprocess import ProcessedMarkdownArtifacts, process_mineru_markdown_artifacts
from app.services.pdf_parser.sections import ParsedPaperSection, SectionArtifacts, split_key_sections


SECTION_CONTEXT_PRIORITY = ["introduction", "method", "experiment", "result", "conclusion"]
ParserProgressCallback = Callable[[str, str], Awaitable[None] | None]


class PDFParserError(RuntimeError):
    """PDF parsing stage error with status code and structured error code."""

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
class ParsedPaperContent:
    text: str
    page_count: int
    char_count: int
    excerpt: str
    sections: list[ParsedPaperSection] = field(default_factory=list)
    artifact_markdown_path: Path | None = None
    artifact_image_dir: Path | None = None
    artifact_section_dir: Path | None = None

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
    """Step 1 parse PDF, step 2 postprocess markdown, step 3 split key sections."""

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

        artifact_dir = artifact_dir or (pdf_path.parent / "mineru")
        bundle = await self._extract_with_mineru(
            pdf_path=pdf_path,
            artifact_dir=artifact_dir,
            progress_callback=progress_callback,
        )

        markdown_path = bundle.markdown_path
        image_dir = bundle.image_dir
        processed_artifacts = await self._postprocess_mineru_artifacts(
            pdf_path=pdf_path,
            bundle=bundle,
            progress_callback=progress_callback,
        )
        if processed_artifacts is not None:
            markdown_path = processed_artifacts.markdown_path
            image_dir = processed_artifacts.figure_dir

        section_artifacts = await self._split_key_sections(
            markdown_path=markdown_path,
            output_dir=pdf_path.parent / "sections",
            progress_callback=progress_callback,
        )
        full_text = section_artifacts.full_text
        if len(full_text) < self.config.pdf_parse_min_chars:
            raise PDFParserError("解析出的 PDF 正文过短，无法继续后续分析。", status_code=422, error_code="PDF_TEXT_TOO_SHORT")

        return ParsedPaperContent(
            text=full_text,
            page_count=max(1, bundle.page_count),
            char_count=len(full_text),
            excerpt=full_text[: self.config.pdf_parse_excerpt_chars],
            sections=section_artifacts.sections,
            artifact_markdown_path=markdown_path,
            artifact_image_dir=image_dir,
            artifact_section_dir=section_artifacts.section_dir,
        )

    async def parse_existing_markdown(
        self,
        markdown_path: Path,
        *,
        image_dir: Path | None = None,
    ) -> ParsedPaperContent:
        if not markdown_path.exists():
            raise PDFParserError("本地 MinerU Markdown 不存在。", status_code=404, error_code="LOCAL_MARKDOWN_NOT_FOUND")

        section_artifacts = await self._split_key_sections(
            markdown_path=markdown_path,
            output_dir=markdown_path.parent / "sections",
            progress_callback=None,
        )
        full_text = section_artifacts.full_text
        if len(full_text) < self.config.pdf_parse_min_chars:
            raise PDFParserError("本地 MinerU Markdown 正文过短。", status_code=422, error_code="LOCAL_MARKDOWN_TOO_SHORT")

        markdown_text = markdown_path.read_text(encoding="utf-8")
        return ParsedPaperContent(
            text=full_text,
            page_count=max(1, markdown_text.count("[Page ")),
            char_count=len(full_text),
            excerpt=full_text[: self.config.pdf_parse_excerpt_chars],
            sections=section_artifacts.sections,
            artifact_markdown_path=markdown_path,
            artifact_image_dir=image_dir if image_dir and image_dir.exists() else None,
            artifact_section_dir=section_artifacts.section_dir,
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
            artifact_section_dir=None,
        )

    def build_llm_context(self, parsed_content: ParsedPaperContent) -> str:
        if parsed_content.sections:
            return self._build_section_context(parsed_content.sections)
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
            await self._emit(progress_callback, "PDF_PARSING_CREATE_JOB", "正在创建 MinerU 解析任务。")
            create_response = await self._create_mineru_job(client, base_url, headers, pdf_path)
            create_payload = self._json_response(
                create_response,
                "MINERU_CREATE_RESPONSE_INVALID",
                "MinerU 创建任务接口返回的不是合法 JSON。",
            )
            if create_payload.get("code") != 0:
                raise PDFParserError("MinerU 拒绝了本次解析任务。", status_code=502, error_code="MINERU_CREATE_REJECTED")

            data = create_payload.get("data") or {}
            batch_id = data.get("batch_id")
            upload_url = (data.get("file_urls") or [None])[0]
            if not batch_id or not upload_url:
                raise PDFParserError(
                    "MinerU 创建任务返回缺少 batch_id 或上传地址。",
                    status_code=502,
                    error_code="MINERU_CREATE_RESPONSE_INCOMPLETE",
                )

            await self._emit(progress_callback, "PDF_PARSING_UPLOAD", "正在上传 PDF 到 MinerU。")
            await self._upload_pdf(client, upload_url, pdf_path)

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

            query_payload = self._json_response(
                query_response,
                "MINERU_STATUS_RESPONSE_INVALID",
                "MinerU 状态接口返回的不是合法 JSON。",
            )
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
        await self._emit(progress_callback, "PDF_PARSING_POSTPROCESS", "正在做 Markdown 后处理与标题归一化。")
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

    async def _split_key_sections(
        self,
        *,
        markdown_path: Path,
        output_dir: Path,
        progress_callback: ParserProgressCallback | None,
    ) -> SectionArtifacts:
        await self._emit(progress_callback, "PDF_PARSING_SPLIT", "正在拆分引言、方法、实验、结果、结论等关键章节。")
        return split_key_sections(markdown_path, output_dir)

    def _build_section_context(self, sections: list[ParsedPaperSection]) -> str:
        available_chars = self.config.llm_pdf_context_chars
        blocks: list[str] = []
        ordered_sections = [section for key in SECTION_CONTEXT_PRIORITY for section in sections if section.key == key]

        for section in ordered_sections:
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
