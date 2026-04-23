from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.schemas.papers import (
    DocumentResponse,
    DocumentUpdateRequest,
    JobResponse,
    PaperCreateRequest,
    PaperListQuery,
    PaperResponse,
    PaperUpdateRequest,
    ParsedContentResponse,
    ParsePaperRequest,
)
from app.services.papers.repository import PaperRepository


class PaperService:
    def __init__(self, repository: PaperRepository | None = None) -> None:
        self.repository = repository or PaperRepository()

    def create_paper(self, request: PaperCreateRequest) -> PaperResponse:
        values = request.model_dump()
        values.pop("download_pdf", None)
        parse_after_import = bool(values.pop("parse_after_import", False))
        paper = self.repository.create_paper(values)
        response = self.to_paper_response(paper)
        if parse_after_import:
            job = self.queue_parse(paper.paper_id, ParsePaperRequest())
            response = self.get_paper(paper.paper_id)
            response.parse_job_id = job.job_id
        return response

    def list_papers(self, query: PaperListQuery) -> tuple[list[PaperResponse], int]:
        papers, total = self.repository.list_papers(query.model_dump())
        return [self.to_paper_response(paper) for paper in papers], total

    def get_paper(self, paper_id: int) -> PaperResponse:
        return self.to_paper_response(self.repository.get_paper(paper_id))

    def update_paper(self, paper_id: int, request: PaperUpdateRequest) -> PaperResponse:
        values = request.model_dump(exclude_unset=True)
        return self.to_paper_response(self.repository.update_paper(paper_id, values))

    def delete_paper(self, paper_id: int) -> None:
        self.repository.delete_paper(paper_id)

    def get_document(self, paper_id: int, doc_role: str) -> DocumentResponse:
        document = self.repository.get_document(paper_id, doc_role)
        return DocumentResponse(
            paper_id=document.paper_id,
            doc_role=document.doc_role,  # type: ignore[arg-type]
            content=document.content,
            version=document.version,
            updated_at=document.updated_at,
        )

    def update_human_document(
        self,
        paper_id: int,
        request: DocumentUpdateRequest,
    ) -> DocumentResponse:
        document = self.repository.update_document(
            paper_id=paper_id,
            doc_role="human",
            content=request.content,
            base_version=request.base_version,
        )
        return DocumentResponse(
            paper_id=document.paper_id,
            doc_role="human",
            content=document.content,
            version=document.version,
            updated_at=document.updated_at,
        )

    def queue_parse(self, paper_id: int, request: ParsePaperRequest) -> JobResponse:
        message = (
            f"Queued {request.parser} parse "
            f"(llm_refine={request.llm_refine}, split_sections={request.split_sections})."
        )
        return self.to_job_response(self.repository.create_parse_job(paper_id, message))

    def get_parsed_content(self, paper_id: int) -> ParsedContentResponse:
        document = self.repository.get_document(paper_id, "llm")
        content = document.content.strip()
        return ParsedContentResponse(
            paper_id=paper_id,
            page_count=max(1, content.count("[Page ")),
            char_count=len(content),
            excerpt=content[:1200],
            sections=[],
            artifacts={"llm_note": document.version},
        )

    def get_job(self, job_id: str) -> JobResponse:
        return self.to_job_response(self.repository.get_job(job_id))

    @staticmethod
    def to_paper_response(record: Any) -> PaperResponse:
        return PaperResponse.model_validate(asdict(record))

    @staticmethod
    def to_job_response(record: Any) -> JobResponse:
        return JobResponse.model_validate(asdict(record))
