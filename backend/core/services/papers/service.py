"""Paper 业务服务。

本模块只接收 core DTO，不依赖 FastAPI schema，保证 Worker 可以独立复用。
"""

from __future__ import annotations

from dataclasses import asdict, replace

from core.services.papers.models import (
    DocumentRecord,
    DocumentUpdateInput,
    JobListInput,
    JobRecord,
    PaperArtifactRecord,
    PaperCreateInput,
    PaperListInput,
    PaperPipelineInput,
    PaperPipelineRecord,
    PaperPipelineRunRecord,
    PaperRecord,
    PaperUpdateInput,
    ParsedContentRecord,
    ParsePaperInput,
    RefineParseInput,
)
from core.services.papers.repository import PaperRepository


class PaperService:
    """编排 Paper 创建、查询、文档更新和动作执行。"""

    def __init__(self, repository: PaperRepository | None = None) -> None:
        """初始化服务依赖的仓储对象。"""

        self.repository = repository or PaperRepository()

    def create_paper(self, request: PaperCreateInput) -> PaperRecord:
        """创建 Paper，并按需立即创建 parse job。"""

        values = asdict(request)
        download_pdf = bool(values.pop("download_pdf", False))
        parse_after_import = bool(values.pop("parse_after_import", False))
        paper = self.repository.create_paper(values)
        download_job_id: str | None = None
        parse_job_id: str | None = None

        if download_pdf or parse_after_import:
            download_job = self.run_download(paper.paper_id)
            download_job_id = download_job.job_id

        if parse_after_import:
            parse_job = self.run_parse(paper.paper_id, ParsePaperInput())
            parse_job_id = parse_job.job_id

        if download_job_id is None and parse_job_id is None:
            return paper
        return replace(
            self.get_paper(paper.paper_id),
            download_job_id=download_job_id,
            parse_job_id=parse_job_id,
        )

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

    def update_document(
        self,
        paper_id: int,
        doc_role: str,
        request: DocumentUpdateInput,
    ) -> DocumentRecord:
        """更新 Paper 指定角色文档。"""

        return self.repository.update_document(
            paper_id=paper_id,
            doc_role=doc_role,
            content=request.content,
            base_version=request.base_version,
        )

    def run_download(self, paper_id: int) -> JobRecord:
        """生成本地占位 PDF，并更新下载状态。"""

        return self.repository.run_download(paper_id)

    def run_parse(self, paper_id: int, request: ParsePaperInput) -> JobRecord:
        """生成 raw markdown。"""

        return self.repository.run_parse(
            paper_id=paper_id,
            parser=request.parser,
            force=request.force,
        )

    def run_refine_parse(self, paper_id: int, request: RefineParseInput) -> JobRecord:
        """生成 refined markdown。"""

        return self.repository.run_refine_parse(paper_id, request)

    def submit_review(self, paper_id: int) -> PaperRecord:
        """将 Paper 置为人工审查中。"""

        return self.repository.submit_review(paper_id)

    def confirm_review(self, paper_id: int) -> PaperRecord:
        """确认人工审查完成。"""

        return self.repository.confirm_review(paper_id)

    def run_split_sections(self, paper_id: int) -> JobRecord:
        """生成 canonical sections。"""

        return self.repository.run_split_sections(paper_id)

    def run_generate_note(self, paper_id: int) -> JobRecord:
        """生成统一 note.md。"""

        return self.repository.run_generate_note(paper_id)

    def run_pipeline(
        self, paper_id: int, request: PaperPipelineInput
    ) -> PaperPipelineRecord:
        """Run the local Paper processing chain in dependency order."""

        jobs: list[JobRecord] = []
        stopped_at: str | None = None
        message = "Paper pipeline completed."

        def append_job(job: JobRecord, stage: str) -> bool:
            nonlocal stopped_at, message
            jobs.append(job)
            if job.status != "succeeded":
                stopped_at = stage
                message = job.message
                return False
            return True

        if request.download_pdf and not append_job(
            self.run_download(paper_id),
            "download",
        ):
            return self._pipeline_record(paper_id, jobs, stopped_at, message)

        if request.parse and not append_job(
            self.run_parse(
                paper_id,
                ParsePaperInput(parser=request.parser, force=request.force_parse),
            ),
            "parse",
        ):
            return self._pipeline_record(paper_id, jobs, stopped_at, message)

        if request.refine_parse and not append_job(
            self.run_refine_parse(
                paper_id,
                RefineParseInput(instruction=request.refine_instruction),
            ),
            "refine",
        ):
            return self._pipeline_record(paper_id, jobs, stopped_at, message)

        if request.require_review_confirmation:
            self.submit_review(paper_id)
            return PaperPipelineRecord(
                paper_id=paper_id,
                status="waiting_review",
                message="Pipeline stopped for manual refined.md review.",
                stopped_at="review",
                jobs=jobs,
                paper=self.get_paper(paper_id),
            )

        if request.split_sections and not append_job(
            self.run_split_sections(paper_id),
            "split",
        ):
            return self._pipeline_record(paper_id, jobs, stopped_at, message)

        if request.generate_note and not append_job(
            self.run_generate_note(paper_id),
            "summarize",
        ):
            return self._pipeline_record(paper_id, jobs, stopped_at, message)

        return self._pipeline_record(paper_id, jobs, stopped_at, message)

    def run_extract_knowledge(self, paper_id: int) -> JobRecord:
        """生成 Knowledge 抽取占位结果。"""

        return self.repository.run_extract_knowledge(paper_id)

    def run_extract_datasets(self, paper_id: int) -> JobRecord:
        """生成 Dataset 抽取占位结果。"""

        return self.repository.run_extract_datasets(paper_id)

    def get_parsed_content(self, paper_id: int) -> ParsedContentRecord:
        """返回 raw/refined/sections 的综合摘要。"""

        payload = self.repository.get_parsed_content(paper_id)
        return ParsedContentRecord(
            paper_id=int(payload["paper_id"]),
            page_count=int(payload["page_count"]),
            char_count=int(payload["char_count"]),
            excerpt=str(payload["excerpt"]),
            sections=list(payload["sections"]),
            artifacts=dict(payload["artifacts"]),
        )

    def list_sections(self, paper_id: int) -> list[dict[str, object]]:
        """读取 canonical sections。"""

        return self.repository.list_sections(paper_id)

    def list_artifacts(self, paper_id: int) -> list[PaperArtifactRecord]:
        return self.repository.list_artifacts(paper_id)

    def list_pipeline_runs(self, paper_id: int) -> list[PaperPipelineRunRecord]:
        return self.repository.list_pipeline_runs(paper_id)

    def get_job(self, job_id: str) -> JobRecord:
        """查询 Paper 相关 job。"""

        return self.repository.get_job(job_id)

    def list_jobs(self, query: JobListInput) -> tuple[list[JobRecord], int]:
        """分页查询任务记录。"""

        return self.repository.list_jobs(asdict(query))

    def cancel_job(self, job_id: str) -> JobRecord:
        """取消仍可取消的任务。"""

        return self.repository.cancel_job(job_id)

    def _pipeline_record(
        self,
        paper_id: int,
        jobs: list[JobRecord],
        stopped_at: str | None,
        message: str,
    ) -> PaperPipelineRecord:
        return PaperPipelineRecord(
            paper_id=paper_id,
            status="failed" if stopped_at else "succeeded",
            message=message,
            stopped_at=stopped_at,
            jobs=jobs,
            paper=self.get_paper(paper_id),
        )
