"""Project orchestration service."""

from __future__ import annotations

from core.services.documents import merge_managed_blocks
from core.services.llm import llm_registry
from core.services.projects.jobs import ProjectJobRecord, ProjectJobStore
from core.services.projects.models import PROJECT_DOCUMENTS, LinkedPaperRecord
from core.services.projects.repository import ProjectRepository
from core.services.projects.tasks.llm import LLMGenerateClient
from core.services.projects.tasks import ProjectTaskInput, render_project_task
from core.services.projects.tasks.runtime import PROJECT_TASK_SPECS


class ProjectTaskService:
    def __init__(
        self,
        repository: ProjectRepository | None = None,
        job_store: ProjectJobStore | None = None,
        llm_client: LLMGenerateClient = llm_registry,
    ) -> None:
        self.repository = repository or ProjectRepository()
        self.job_store = job_store or ProjectJobStore(self.repository.db_path)
        self.llm_client = llm_client

    def run_refresh_overview(
        self,
        project_id: int,
        task_input: ProjectTaskInput,
    ) -> ProjectJobRecord:
        return self.run_task(project_id, "project_refresh_overview", task_input)

    def run_generate_related_work(
        self,
        project_id: int,
        task_input: ProjectTaskInput,
    ) -> ProjectJobRecord:
        return self.run_task(project_id, "project_generate_related_work", task_input)

    def run_generate_method(
        self,
        project_id: int,
        task_input: ProjectTaskInput,
    ) -> ProjectJobRecord:
        return self.run_task(project_id, "project_generate_method", task_input)

    def run_generate_experiment(
        self,
        project_id: int,
        task_input: ProjectTaskInput,
    ) -> ProjectJobRecord:
        return self.run_task(project_id, "project_generate_experiment", task_input)

    def run_generate_conclusion(
        self,
        project_id: int,
        task_input: ProjectTaskInput,
    ) -> ProjectJobRecord:
        return self.run_task(project_id, "project_generate_conclusion", task_input)

    def run_generate_manuscript(
        self,
        project_id: int,
        task_input: ProjectTaskInput,
    ) -> ProjectJobRecord:
        return self.run_task(project_id, "project_generate_manuscript", task_input)

    def run_task(
        self,
        project_id: int,
        task_type: str,
        task_input: ProjectTaskInput,
    ) -> ProjectJobRecord:
        project = self.repository.get_project(project_id)
        linked_papers = self._filter_linked_papers(
            self.repository.list_linked_papers(project_id),
            task_input.included_paper_ids,
        )
        documents = {
            role: self.repository.get_document(project_id, role).content
            for role, _, _ in PROJECT_DOCUMENTS
        }
        recent_jobs = self.job_store.list_recent(project_id=project_id)
        task_result = render_project_task(
            task_type=task_type,
            project=project,
            linked_papers=linked_papers,
            documents=documents,
            recent_jobs=recent_jobs,
            task_input=task_input,
            llm_client=self.llm_client,
        )
        current_document = self.repository.get_document(project_id, task_result.doc_role)
        merged_content = merge_managed_blocks(
            existing=current_document.content,
            generated=task_result.content,
            block_order=task_result.block_ids,
            skip_locked_blocks=task_input.skip_locked_blocks,
        )
        updated_document = self.repository.update_document(
            project_id=project_id,
            doc_role=task_result.doc_role,
            content=merged_content,
            base_version=None,
        )
        return self.job_store.create_job(
            project_id=project_id,
            job_type=PROJECT_TASK_SPECS[task_type].job_type,
            status="succeeded",
            progress=1.0,
            message=task_result.message,
            result={
                **task_result.result,
                "document_version": updated_document.version,
                "output_doc_role": updated_document.doc_role,
            },
        )

    def _filter_linked_papers(
        self,
        linked_papers: list[LinkedPaperRecord],
        included_paper_ids: tuple[int, ...],
    ) -> list[LinkedPaperRecord]:
        if not included_paper_ids:
            return linked_papers
        allowed = set(included_paper_ids)
        return [paper for paper in linked_papers if paper.paper_id in allowed]
