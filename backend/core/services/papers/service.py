"""Paper 业务服务。

本模块只接收 core DTO，不依赖 FastAPI schema，保证 Worker 可以独立复用。
"""

from __future__ import annotations

from dataclasses import asdict, replace

from core.services.papers.models import (
    DocumentRecord,
    DocumentUpdateInput,
    JobRecord,
    PaperCreateInput,
    PaperListInput,
    PaperRecord,
    PaperUpdateInput,
    ParsedContentRecord,
    ParsePaperInput,
)
from core.services.papers.repository import PaperRepository


class PaperService:
    """编排 Paper 创建、查询、文档更新和 parse job 创建。"""

    def __init__(self, repository: PaperRepository | None = None) -> None:
        """初始化服务依赖的仓储对象。"""

        self.repository = repository or PaperRepository()

    def create_paper(self, request: PaperCreateInput) -> PaperRecord:
        """创建 Paper，并按需立即创建 parse job。"""

        values = asdict(request)
        values.pop("download_pdf", None)
        parse_after_import = bool(values.pop("parse_after_import", False))
        paper = self.repository.create_paper(values)
        if not parse_after_import:
            return paper

        job = self.queue_parse(paper.paper_id, ParsePaperInput())
        return replace(self.get_paper(paper.paper_id), parse_job_id=job.job_id)

    def list_papers(self, query: PaperListInput) -> tuple[list[PaperRecord], int]:
        """按查询条件列出 Paper 记录。"""

        return self.repository.list_papers(asdict(query))

    def get_paper(self, paper_id: int) -> PaperRecord:
        """查询单个 Paper。"""

        return self.repository.get_paper(paper_id)

    def update_paper(self, paper_id: int, request: PaperUpdateInput) -> PaperRecord:
        """更新 Paper 元数据。"""

        return self.repository.update_paper(paper_id, request.values)

    def delete_paper(self, paper_id: int) -> None:
        """软删除 Paper。"""

        self.repository.delete_paper(paper_id)

    def get_document(self, paper_id: int, doc_role: str) -> DocumentRecord:
        """读取 Paper 指定角色文档。"""

        return self.repository.get_document(paper_id, doc_role)

    def update_human_document(
        self,
        paper_id: int,
        request: DocumentUpdateInput,
    ) -> DocumentRecord:
        """更新 Paper 的人工笔记文档。"""

        return self.repository.update_document(
            paper_id=paper_id,
            doc_role="human",
            content=request.content,
            base_version=request.base_version,
        )

    def queue_parse(self, paper_id: int, request: ParsePaperInput) -> JobRecord:
        """创建 Paper parse job 记录。"""

        message = (
            f"Queued {request.parser} parse "
            f"(llm_refine={request.llm_refine}, split_sections={request.split_sections})."
        )
        return self.repository.create_parse_job(paper_id, message)

    def get_parsed_content(self, paper_id: int) -> ParsedContentRecord:
        """基于当前 LLM 文档返回解析内容摘要。"""

        document = self.repository.get_document(paper_id, "llm")
        content = document.content.strip()
        return ParsedContentRecord(
            paper_id=paper_id,
            page_count=max(1, content.count("[Page ")),
            char_count=len(content),
            excerpt=content[:1200],
            sections=[],
            artifacts={"llm_note": document.version},
        )

    def get_job(self, job_id: str) -> JobRecord:
        """查询 Paper 相关 job。"""

        return self.repository.get_job(job_id)
