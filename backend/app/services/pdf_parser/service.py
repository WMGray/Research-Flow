from __future__ import annotations

import asyncio
from collections.abc import Awaitable
import json
from pathlib import Path
import shutil
from typing import Any

import httpx

from app.core.config import Settings
from app.core.mineru_config import MinerUConfig
from app.core.pdf_parser_config import PDFParserConfig
from app.services.llm.registry import llm_registry
from app.services.pdf_parser.context import build_parsed_content_llm_context
from app.services.pdf_parser.markdown_refine import LLMGenerateClient, refine_markdown_with_llm
from app.services.pdf_parser.models import (
    MinerUExtractionResult,
    ParsedPaperContent,
    ParserProgressCallback,
    PDFParserError,
)
from app.services.pdf_parser.postprocess import ProcessedMarkdownArtifacts, process_mineru_markdown_artifacts
from app.services.pdf_parser.sections import SectionArtifacts, split_key_sections


class PDFParserService:
    """Parse PDF, postprocess artifacts, refine Markdown, then split sections."""

    def __init__(
        self,
        settings: Settings | MinerUConfig,
        *,
        pdf_parser_config: PDFParserConfig | None = None,
        llm_client: LLMGenerateClient | None = None,
    ) -> None:
        self.config = settings.mineru if isinstance(settings, Settings) else settings
        self.pdf_parser_config = (
            pdf_parser_config
            if pdf_parser_config is not None
            else settings.pdf_parser if isinstance(settings, Settings) else PDFParserConfig()
        )
        self.llm_client = llm_client or llm_registry

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

        markdown_path = await self._refine_markdown_format(
            markdown_path=markdown_path,
            output_path=pdf_path.parent / self.pdf_parser_config.markdown_refine.output_filename,
            progress_callback=progress_callback,
        )

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

        markdown_path = await self._refine_markdown_format(
            markdown_path=markdown_path,
            output_path=markdown_path.parent / self.pdf_parser_config.markdown_refine.output_filename,
            progress_callback=None,
        )

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
        return build_parsed_content_llm_context(
            parsed_content,
            context_chars=self.config.llm_pdf_context_chars,
            section_chars=self.config.llm_pdf_section_chars,
        )

    async def _extract_with_mineru(
        self,
        *,
        pdf_path: Path,
        artifact_dir: Path,
        progress_callback: ParserProgressCallback | None,
    ) -> MinerUExtractionResult:
        await self._emit(progress_callback, "PDF_PARSING_CREATE_JOB", "正在通过官方 MinerU SDK 解析 PDF。")
        return await asyncio.to_thread(self._extract_with_mineru_sync, pdf_path, artifact_dir)

    def _extract_with_mineru_sync(self, pdf_path: Path, artifact_dir: Path) -> MinerUExtractionResult:
        MinerU, exceptions = self._load_mineru_sdk()

        if artifact_dir.exists():
            shutil.rmtree(artifact_dir)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        client = MinerU(
            token=self.config.api_token,
            base_url=self._sdk_base_url(),
        )
        api_client = client._require_auth()
        api_client.download = self._download_sdk_result
        try:
            result = client.extract(
                str(pdf_path),
                model=self.config.model,
                formula=True,
                table=True,
                timeout=int(self.config.poll_timeout_seconds),
            )
        except exceptions["AuthError"] as exc:
            raise PDFParserError("MinerU 认证失败，请检查 API Token。", status_code=502, error_code="MINERU_AUTH_FAILED", raw_error_detail=str(exc)) from exc
        except exceptions["TimeoutError"] as exc:
            raise PDFParserError("等待 MinerU 返回解析结果超时。", status_code=504, error_code="MINERU_TIMEOUT", raw_error_detail=str(exc)) from exc
        except exceptions["MinerUError"] as exc:
            raise PDFParserError("MinerU 解析失败。", status_code=502, error_code="MINERU_SDK_ERROR", raw_error_detail=str(exc)) from exc
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

        if result.state != "done" or not result.markdown:
            raise PDFParserError("MinerU 没有返回有效的 Markdown 结果。", status_code=502, error_code="MINERU_MARKDOWN_MISSING")

        try:
            result.save_all(str(artifact_dir))
        except Exception:
            self._save_sdk_result_locally(result, artifact_dir)

        markdown_path = artifact_dir / "full.md"
        if not markdown_path.exists():
            markdown_path.write_text(result.markdown, encoding="utf-8")

        image_dir = artifact_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        if not any(image_dir.iterdir()) and result.images:
            for image in result.images:
                (image_dir / image.name).write_bytes(image.data)

        content_list_path = self._resolve_content_list_path(artifact_dir)
        if content_list_path is None and result.content_list is not None:
            content_list_path = artifact_dir / "content_list_v2.json"
            content_list_path.write_text(
                json.dumps(result.content_list, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        page_count = len(result.content_list or []) or self._page_count_from_markdown(result.markdown)
        return MinerUExtractionResult(
            markdown_text=result.markdown,
            markdown_path=markdown_path,
            image_dir=image_dir,
            page_count=max(1, page_count),
            content_list_path=content_list_path,
        )

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
                output_markdown_path=pdf_path.parent / "note.md",
                output_figure_dir=pdf_path.parent / "figures",
            )
        except Exception:
            return None

    async def _refine_markdown_format(
        self,
        *,
        markdown_path: Path,
        output_path: Path,
        progress_callback: ParserProgressCallback | None,
    ) -> Path:
        refine_config = self.pdf_parser_config.markdown_refine
        if not refine_config.enabled:
            return markdown_path

        await self._emit(progress_callback, "PDF_PARSING_LLM_REFINE", "正在通过 LLM 优化 Markdown 格式。")
        result = await refine_markdown_with_llm(
            markdown_path=markdown_path,
            output_path=output_path,
            config=refine_config,
            llm_client=self.llm_client,
        )
        if result.error:
            await self._emit(
                progress_callback,
                "PDF_PARSING_LLM_REFINE_SKIPPED",
                f"LLM Markdown 调优未生效，继续使用原始 Markdown：{result.error}",
            )
        return result.markdown_path

    async def _split_key_sections(
        self,
        *,
        markdown_path: Path,
        output_dir: Path,
        progress_callback: ParserProgressCallback | None,
    ) -> SectionArtifacts:
        await self._emit(progress_callback, "PDF_PARSING_SPLIT", "正在拆分引言、方法、实验、结果、结论等关键章节。")
        return split_key_sections(markdown_path, output_dir)

    def _sdk_base_url(self) -> str:
        base_url = self.config.base_url.rstrip("/")
        return base_url if base_url.endswith("/api/v4") else f"{base_url}/api/v4"

    @staticmethod
    def _candidate_download_urls(zip_url: str) -> list[str]:
        candidate_urls = [zip_url]
        cdn_prefix = "https://cdn-mineru.openxlab.org.cn"
        oss_prefix = "https://mineru.oss-cn-shanghai.aliyuncs.com"
        if zip_url.startswith(cdn_prefix):
            candidate_urls.append(zip_url.replace(cdn_prefix, oss_prefix, 1))
        return candidate_urls

    def _download_sdk_result(self, zip_url: str) -> bytes:
        last_error: Exception | None = None
        for candidate_url in self._candidate_download_urls(zip_url):
            try:
                response = httpx.get(
                    candidate_url,
                    timeout=httpx.Timeout(30.0, read=300.0),
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.content
            except Exception as exc:  # noqa: BLE001 - re-raised below with the last error
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("Failed to download MinerU result ZIP.")

    @staticmethod
    def _resolve_content_list_path(artifact_dir: Path) -> Path | None:
        candidates = [
            artifact_dir / "content_list_v2.json",
            artifact_dir / "content_list.json",
            *sorted(artifact_dir.glob("*_content_list.json")),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _save_sdk_result_locally(result: Any, artifact_dir: Path) -> None:
        markdown_path = artifact_dir / "full.md"
        markdown_path.write_text(result.markdown or "", encoding="utf-8")

        image_dir = artifact_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        for image in result.images or []:
            (image_dir / image.name).write_bytes(image.data)

        if result.content_list is not None:
            (artifact_dir / "content_list_v2.json").write_text(
                json.dumps(result.content_list, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    @staticmethod
    def _load_mineru_sdk() -> tuple[Any, dict[str, Any]]:
        try:
            from mineru import AuthError, MinerU, MinerUError, TimeoutError
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "mineru-open-sdk is required for pdf_parser. Run `uv sync` in backend after updating dependencies."
            ) from exc
        return MinerU, {
            "AuthError": AuthError,
            "TimeoutError": TimeoutError,
            "MinerUError": MinerUError,
        }

    @staticmethod
    def _page_count_from_markdown(markdown_text: str) -> int:
        return markdown_text.count("[Page ") if markdown_text else 0

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
