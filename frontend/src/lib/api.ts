import {
  API_BASE_URL,
  APIError,
  request,
  type APIEnvelope,
} from "@/lib/http";
import {
  cancelJob,
  getJob,
  listJobs,
  type JobListResponse,
  type JobRecord,
} from "@/lib/jobs";

export { APIError, cancelJob, getJob, listJobs };
export type { APIEnvelope, JobListResponse, JobRecord };

export type PaperRecord = {
  paper_id: number;
  asset_id: number;
  title: string;
  paper_slug: string;
  abstract: string;
  authors: string[];
  year: number | null;
  venue: string;
  venue_short: string;
  ccf_rank: string;
  sci_quartile: string;
  doi: string;
  source_url: string;
  pdf_url: string;
  source_kind: "manual" | "search" | "feed" | "zotero";
  category_id: number | null;
  tags: string[];
  paper_stage: string;
  download_status: string;
  parse_status: string;
  refine_status: string;
  review_status: string;
  note_status: string;
  assets: Record<string, number>;
  created_at: string;
  updated_at: string;
  download_job_id: string | null;
  parse_job_id: string | null;
  latest_job_id: string | null;
  latest_job_type: string;
  latest_job_status: string;
  latest_job_message: string;
  source_pdf_size: number;
  source_pdf_is_real: boolean;
};

export type PaperListResponse = {
  papers: PaperRecord[];
  total: number;
  page: number;
  pageSize: number;
};

export type CategoryRecord = {
  category_id: number;
  name: string;
  parent_id: number | null;
  path: string;
  sort_order: number;
  children?: CategoryRecord[];
};

export type DatasetRecord = {
  dataset_id: number;
  asset_id: number;
  name: string;
  normalized_name: string;
  aliases: string[];
  task_type: string;
  data_domain: string;
  scale: string;
  source: string;
  description: string;
  access_url: string;
  benchmark_summary: string;
  created_at: string;
  updated_at: string;
};

export type KnowledgeRecord = {
  knowledge_id: number;
  asset_id: number;
  knowledge_type: "view" | "definition";
  title: string;
  summary_zh: string;
  original_text_en: string;
  citation_marker: string;
  category_label: string;
  research_field: string;
  source_paper_asset_id: number | null;
  source_section: string;
  source_locator: string;
  evidence_text: string;
  confidence_score: number;
  review_status: "pending_review" | "accepted" | "rejected";
  llm_run_id: string;
  created_at: string;
  updated_at: string;
};

export type ProjectRecord = {
  project_id: number;
  asset_id: number;
  name: string;
  project_slug: string;
  status: "planning" | "researching" | "experimenting" | "writing" | "archived";
  summary: string;
  owner: string;
  assets: Record<string, number>;
  created_at: string;
  updated_at: string;
};

export type ProjectDocumentRecord = {
  project_id: number;
  doc_id: number;
  doc_role:
    | "overview"
    | "related_work"
    | "method"
    | "experiment"
    | "conclusion"
    | "manuscript";
  content: string;
  version: number;
  updated_at: string;
};

export type AgentProfileRecord = {
  profile_key: string;
  scene: string;
  provider: string;
  model_name: string;
  temperature: number | null;
  max_tokens: number | null;
  enabled: boolean;
  updated_at: string;
};

export type SkillCatalogRecord = {
  skill_name: string;
  description: string;
  path: string;
  has_runtime_instructions: boolean;
  has_agent_metadata: boolean;
};

export type SkillBindingRecord = {
  skill_key: string;
  scene: string;
  agent_profile_key: string;
  runtime_instruction_key: string;
  toolset: string[];
  enabled: boolean;
  updated_at: string;
};

export type LLMStatusRecord = {
  profile_key: string;
  provider: string;
  model_name: string;
  connectivity_status: string;
  ttft_ms: number | null;
  checked_at: string;
  error_message: string;
};

export type FeedItemRecord = {
  item_id: number;
  paper_id: number;
  title: string;
  abstract: string;
  authors: string[];
  year: number | null;
  venue: string;
  source_url: string;
  pdf_url: string;
  score: number;
  reason: string;
  topic: string;
  status: "candidate" | "saved" | "dismissed";
  source: string;
  feed_date: string;
  created_at: string;
  updated_at: string;
};

export type ConferenceRecord = {
  conference_id: number;
  name: string;
  acronym: string;
  year: number;
  rank: string;
  field: string;
  abstract_deadline: string;
  paper_deadline: string;
  notification_date: string;
  status: "tracking" | "submitted" | "accepted" | "rejected" | "archived";
  url: string;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type RecommendationRecord = {
  recommendation_id: string;
  target_type: string;
  target_id: number;
  title: string;
  reason: string;
  score: number;
  action: string;
  metadata: Record<string, string | number | boolean | null>;
};

export type GraphNodeRecord = {
  id: string;
  label: string;
  type: string;
  metadata: Record<string, string | number | boolean | null>;
};

export type GraphEdgeRecord = {
  id: string;
  source: string;
  target: string;
  relation: string;
  metadata: Record<string, string | number | boolean | null>;
};

export type PaperPipelineResponse = {
  paper_id: number;
  status: "succeeded" | "failed" | "waiting_review";
  message: string;
  stopped_at: string | null;
  jobs: JobRecord[];
  paper: PaperRecord;
};

export type FeedListResponse = {
  items: FeedItemRecord[];
  total: number;
  page: number;
  pageSize: number;
};

export type ConferenceListResponse = {
  conferences: ConferenceRecord[];
  total: number;
  page: number;
  pageSize: number;
};

export type GraphResponse = {
  nodes: GraphNodeRecord[];
  edges: GraphEdgeRecord[];
};

export type DatasetListResponse = {
  datasets: DatasetRecord[];
  total: number;
  page: number;
  pageSize: number;
};

export type KnowledgeListResponse = {
  knowledge: KnowledgeRecord[];
  total: number;
  page: number;
  pageSize: number;
};

export type ProjectListResponse = {
  projects: ProjectRecord[];
  total: number;
  page: number;
  pageSize: number;
};

export type PaperResolveMode = "source_url" | "doi" | "title";

export type PaperResolveResponse = {
  raw_input: string;
  title: string;
  authors: string[];
  year: string;
  venue: string;
  ccf_rank: string;
  sci_quartile: string;
  doi: string;
  resolve_method: string;
  source: string;
  status: string;
  pdf_url: string;
  landing_url: string;
  final_url: string;
  http_status: string;
  content_type: string;
  detail: string;
  error_code: string;
  metadata_source: string;
  metadata_confidence: string;
  suggested_filename: string;
  target_path: string;
  probe_trace: string[];
};

export type PaperCreateInput = {
  title: string;
  abstract?: string;
  authors?: string[];
  year?: number | null;
  venue?: string;
  venue_short?: string;
  ccf_rank?: string;
  sci_quartile?: string;
  doi?: string;
  source_url?: string;
  pdf_url?: string;
  source_kind?: PaperRecord["source_kind"];
  category_id?: number | null;
  tags?: string[];
  download_pdf?: boolean;
  parse_after_import?: boolean;
};

export type PaperUpdateInput = Partial<
  Pick<
    PaperCreateInput,
    | "title"
    | "abstract"
    | "authors"
    | "year"
    | "venue"
    | "venue_short"
    | "ccf_rank"
    | "sci_quartile"
    | "doi"
    | "source_url"
    | "pdf_url"
    | "source_kind"
    | "category_id"
    | "tags"
  >
>;

export type DatasetCreateInput = {
  name: string;
  normalized_name?: string;
  aliases?: string[];
  task_type?: string;
  data_domain?: string;
  scale?: string;
  source?: string;
  description?: string;
  access_url?: string;
  benchmark_summary?: string;
};

export type DatasetUpdateInput = Partial<DatasetCreateInput>;

export type KnowledgeCreateInput = {
  knowledge_type?: KnowledgeRecord["knowledge_type"];
  title: string;
  summary_zh?: string;
  original_text_en?: string;
  citation_marker?: string;
  category_label?: string;
  research_field?: string;
  source_paper_asset_id?: number | null;
  source_section?: string;
  source_locator?: string;
  evidence_text?: string;
  confidence_score?: number;
  review_status?: KnowledgeRecord["review_status"];
  llm_run_id?: string;
};

export type KnowledgeUpdateInput = Partial<KnowledgeCreateInput>;

export type ProjectCreateInput = {
  name: string;
  summary?: string;
  owner?: string;
  status?: ProjectRecord["status"];
};

export type ProjectTaskInput = {
  focus_instructions?: string;
  included_paper_ids?: number[];
  included_knowledge_ids?: number[];
  included_dataset_ids?: number[];
  skip_locked_blocks?: boolean;
};

export type ConferenceCreateInput = {
  name: string;
  acronym: string;
  year: number;
  rank?: string;
  field?: string;
  abstract_deadline?: string;
  paper_deadline?: string;
  notification_date?: string;
  status?: ConferenceRecord["status"];
  url?: string;
  notes?: string;
};

export type ConferenceUpdateInput = Partial<ConferenceCreateInput>;

export async function listPapers(
  params: {
    q?: string;
    categoryId?: number | null;
    paperStage?: string | null;
    yearFrom?: number | null;
    yearTo?: number | null;
    sort?: string;
    order?: "asc" | "desc";
    page?: number;
    pageSize?: number;
  } = {},
  signal?: AbortSignal,
): Promise<PaperListResponse> {
  const query = new URLSearchParams();
  if (params.q) {
    query.set("q", params.q);
  }
  if (params.categoryId !== undefined && params.categoryId !== null) {
    query.set("category_id", String(params.categoryId));
  }
  if (params.paperStage) {
    query.set("paper_stage", params.paperStage);
  }
  if (params.yearFrom !== undefined && params.yearFrom !== null) {
    query.set("year_from", String(params.yearFrom));
  }
  if (params.yearTo !== undefined && params.yearTo !== null) {
    query.set("year_to", String(params.yearTo));
  }
  if (params.sort) {
    query.set("sort", params.sort);
  }
  if (params.order) {
    query.set("order", params.order);
  }
  query.set("page", String(params.page ?? 1));
  query.set("page_size", String(params.pageSize ?? 20));

  const envelope = await request<PaperRecord[]>(
    `/api/v1/papers?${query.toString()}`,
    { signal },
  );

  return {
    papers: envelope.data,
    total: Number(envelope.meta.total ?? envelope.data.length),
    page: Number(envelope.meta.page ?? params.page ?? 1),
    pageSize: Number(envelope.meta.page_size ?? params.pageSize ?? 20),
  };
}

export async function resolvePaper(input: {
  mode: PaperResolveMode;
  value: string;
}): Promise<PaperResolveResponse> {
  const envelope = await request<PaperResolveResponse>("/api/v1/papers/resolve", {
    method: "POST",
    body: { [input.mode]: input.value },
  });
  return envelope.data;
}

export async function createPaper(input: PaperCreateInput): Promise<PaperRecord> {
  const envelope = await request<PaperRecord>("/api/v1/papers", {
    method: "POST",
    body: input,
  });
  return envelope.data;
}

export async function updatePaper(
  paperId: number,
  input: PaperUpdateInput,
): Promise<PaperRecord> {
  const envelope = await request<PaperRecord>(`/api/v1/papers/${paperId}`, {
    method: "PATCH",
    body: input,
  });
  return envelope.data;
}

export async function listCategories(): Promise<CategoryRecord[]> {
  const envelope = await request<CategoryRecord[]>("/api/v1/categories");
  return envelope.data;
}

export async function createCategory(input: {
  name: string;
  parent_id?: number | null;
  sort_order?: number;
}): Promise<CategoryRecord> {
  const envelope = await request<CategoryRecord>("/api/v1/categories", {
    method: "POST",
    body: {
      name: input.name,
      parent_id: input.parent_id ?? null,
      sort_order: input.sort_order ?? 0,
    },
  });
  return envelope.data;
}

export async function runPaperPipeline(
  paperId: number,
  input: {
    download_pdf?: boolean;
    parse?: boolean;
    refine_parse?: boolean;
    split_sections?: boolean;
    generate_note?: boolean;
    require_review_confirmation?: boolean;
  } = {},
): Promise<PaperPipelineResponse> {
  const envelope = await request<PaperPipelineResponse>(
    `/api/v1/papers/${paperId}/pipeline`,
    {
      method: "POST",
      body: input,
    },
  );
  return envelope.data;
}

export async function confirmPaperReview(paperId: number): Promise<PaperRecord> {
  const envelope = await request<PaperRecord>(
    `/api/v1/papers/${paperId}/confirm-review`,
    { method: "POST" },
  );
  return envelope.data;
}

export async function runPaperAction(
  paperId: number,
  action:
    | "split-sections"
    | "generate-note"
    | "extract-knowledge"
    | "extract-datasets",
): Promise<JobRecord> {
  const envelope = await request<JobRecord>(
    `/api/v1/papers/${paperId}/${action}`,
    { method: "POST" },
  );
  return envelope.data;
}

export async function listDatasets(input: {
  q?: string;
  taskType?: string;
  page?: number;
  pageSize?: number;
} = {}): Promise<DatasetListResponse> {
  const params = new URLSearchParams();
  params.set("page", String(input.page ?? 1));
  params.set("page_size", String(input.pageSize ?? 20));
  if (input.q) {
    params.set("q", input.q);
  }
  if (input.taskType) {
    params.set("task_type", input.taskType);
  }
  const envelope = await request<DatasetRecord[]>(
    `/api/v1/datasets?${params.toString()}`,
  );
  return {
    datasets: envelope.data,
    total: Number(envelope.meta.total ?? envelope.data.length),
    page: Number(envelope.meta.page ?? input.page ?? 1),
    pageSize: Number(envelope.meta.page_size ?? input.pageSize ?? 20),
  };
}

export async function createDataset(
  input: DatasetCreateInput,
): Promise<DatasetRecord> {
  const envelope = await request<DatasetRecord>("/api/v1/datasets", {
    method: "POST",
    body: input,
  });
  return envelope.data;
}

export async function updateDataset(
  datasetId: number,
  input: DatasetUpdateInput,
): Promise<DatasetRecord> {
  const envelope = await request<DatasetRecord>(`/api/v1/datasets/${datasetId}`, {
    method: "PATCH",
    body: input,
  });
  return envelope.data;
}

export async function deleteDataset(datasetId: number): Promise<void> {
  await request<unknown>(`/api/v1/datasets/${datasetId}`, { method: "DELETE" });
}

export async function listKnowledge(input: {
  q?: string;
  knowledgeType?: KnowledgeRecord["knowledge_type"] | "";
  reviewStatus?: KnowledgeRecord["review_status"] | "";
  sourcePaperAssetId?: number | null;
  page?: number;
  pageSize?: number;
} = {}): Promise<KnowledgeListResponse> {
  const params = new URLSearchParams();
  params.set("page", String(input.page ?? 1));
  params.set("page_size", String(input.pageSize ?? 20));
  if (input.q) {
    params.set("q", input.q);
  }
  if (input.knowledgeType) {
    params.set("knowledge_type", input.knowledgeType);
  }
  if (input.reviewStatus) {
    params.set("review_status", input.reviewStatus);
  }
  if (input.sourcePaperAssetId !== undefined && input.sourcePaperAssetId !== null) {
    params.set("source_paper_asset_id", String(input.sourcePaperAssetId));
  }
  const envelope = await request<KnowledgeRecord[]>(
    `/api/v1/knowledge?${params.toString()}`,
  );
  return {
    knowledge: envelope.data,
    total: Number(envelope.meta.total ?? envelope.data.length),
    page: Number(envelope.meta.page ?? input.page ?? 1),
    pageSize: Number(envelope.meta.page_size ?? input.pageSize ?? 20),
  };
}

export async function createKnowledge(
  input: KnowledgeCreateInput,
): Promise<KnowledgeRecord> {
  const envelope = await request<KnowledgeRecord>("/api/v1/knowledge", {
    method: "POST",
    body: input,
  });
  return envelope.data;
}

export async function updateKnowledge(
  knowledgeId: number,
  input: KnowledgeUpdateInput,
): Promise<KnowledgeRecord> {
  const envelope = await request<KnowledgeRecord>(
    `/api/v1/knowledge/${knowledgeId}`,
    {
      method: "PATCH",
      body: input,
    },
  );
  return envelope.data;
}

export async function deleteKnowledge(knowledgeId: number): Promise<void> {
  await request<unknown>(`/api/v1/knowledge/${knowledgeId}`, {
    method: "DELETE",
  });
}

export async function refreshFeed(input: {
  feedDate?: string;
  topic?: string;
  source?: "arxiv" | "paper_library";
  categories?: string[];
  query?: string;
  limit?: number;
} = {}): Promise<FeedItemRecord[]> {
  const envelope = await request<FeedItemRecord[]>("/api/v1/feed/refresh", {
    method: "POST",
    body: {
      feed_date: input.feedDate ?? "",
      topic: input.topic ?? "",
      source: input.source ?? "arxiv",
      categories: input.categories ?? [],
      query: input.query ?? "",
      limit: input.limit ?? 20,
    },
  });
  return envelope.data;
}

export async function listFeedItems(input: {
  feedDate?: string;
  q?: string;
  status?: FeedItemRecord["status"] | "";
  page?: number;
  pageSize?: number;
} = {}): Promise<FeedListResponse> {
  const params = new URLSearchParams();
  params.set("page", String(input.page ?? 1));
  params.set("page_size", String(input.pageSize ?? 20));
  if (input.feedDate) {
    params.set("feed_date", input.feedDate);
  }
  if (input.q) {
    params.set("q", input.q);
  }
  if (input.status) {
    params.set("status", input.status);
  }
  const envelope = await request<FeedItemRecord[]>(
    `/api/v1/feed/items?${params.toString()}`,
  );
  return {
    items: envelope.data,
    total: Number(envelope.meta.total ?? envelope.data.length),
    page: Number(envelope.meta.page ?? input.page ?? 1),
    pageSize: Number(envelope.meta.page_size ?? input.pageSize ?? 20),
  };
}

export async function updateFeedItem(
  itemId: number,
  input: Partial<Pick<FeedItemRecord, "status" | "topic" | "reason" | "score">>,
): Promise<FeedItemRecord> {
  const envelope = await request<FeedItemRecord>(`/api/v1/feed/items/${itemId}`, {
    method: "PATCH",
    body: input,
  });
  return envelope.data;
}

export async function listConferences(input: {
  q?: string;
  status?: ConferenceRecord["status"] | "";
  page?: number;
  pageSize?: number;
} = {}): Promise<ConferenceListResponse> {
  const params = new URLSearchParams();
  params.set("page", String(input.page ?? 1));
  params.set("page_size", String(input.pageSize ?? 20));
  if (input.q) {
    params.set("q", input.q);
  }
  if (input.status) {
    params.set("status", input.status);
  }
  const envelope = await request<ConferenceRecord[]>(
    `/api/v1/conferences?${params.toString()}`,
  );
  return {
    conferences: envelope.data,
    total: Number(envelope.meta.total ?? envelope.data.length),
    page: Number(envelope.meta.page ?? input.page ?? 1),
    pageSize: Number(envelope.meta.page_size ?? input.pageSize ?? 20),
  };
}

export async function createConference(
  input: ConferenceCreateInput,
): Promise<ConferenceRecord> {
  const envelope = await request<ConferenceRecord>("/api/v1/conferences", {
    method: "POST",
    body: input,
  });
  return envelope.data;
}

export async function updateConference(
  conferenceId: number,
  input: ConferenceUpdateInput,
): Promise<ConferenceRecord> {
  const envelope = await request<ConferenceRecord>(
    `/api/v1/conferences/${conferenceId}`,
    {
      method: "PATCH",
      body: input,
    },
  );
  return envelope.data;
}

export async function listRecommendations(input: {
  limit?: number;
} = {}): Promise<RecommendationRecord[]> {
  const params = new URLSearchParams();
  params.set("limit", String(input.limit ?? 10));
  const envelope = await request<RecommendationRecord[]>(
    `/api/v1/recommendations?${params.toString()}`,
  );
  return envelope.data;
}

export async function getGraph(input: { limit?: number } = {}): Promise<GraphResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(input.limit ?? 200));
  const envelope = await request<GraphResponse>(`/api/v1/graph?${params.toString()}`);
  return envelope.data;
}

export async function listProjects(input: {
  q?: string;
  status?: ProjectRecord["status"];
  page?: number;
  pageSize?: number;
} = {}): Promise<ProjectListResponse> {
  const params = new URLSearchParams();
  params.set("page", String(input.page ?? 1));
  params.set("page_size", String(input.pageSize ?? 20));
  if (input.q) {
    params.set("q", input.q);
  }
  if (input.status) {
    params.set("status", input.status);
  }
  const envelope = await request<ProjectRecord[]>(
    `/api/v1/projects?${params.toString()}`,
  );
  return {
    projects: envelope.data,
    total: Number(envelope.meta.total ?? envelope.data.length),
    page: Number(envelope.meta.page ?? input.page ?? 1),
    pageSize: Number(envelope.meta.page_size ?? input.pageSize ?? 20),
  };
}

export async function createProject(
  input: ProjectCreateInput,
): Promise<ProjectRecord> {
  const envelope = await request<ProjectRecord>("/api/v1/projects", {
    method: "POST",
    body: input,
  });
  return envelope.data;
}

export async function getProjectDocument(
  projectId: number,
  docRole: ProjectDocumentRecord["doc_role"],
): Promise<ProjectDocumentRecord> {
  const envelope = await request<ProjectDocumentRecord>(
    `/api/v1/projects/${projectId}/documents/${docRole}`,
  );
  return envelope.data;
}

export async function runProjectAction(
  projectId: number,
  action:
    | "refresh-overview"
    | "generate-related-work"
    | "generate-method"
    | "generate-experiment"
    | "generate-conclusion"
    | "generate-manuscript",
  input: ProjectTaskInput = {},
): Promise<JobRecord> {
  const envelope = await request<JobRecord>(`/api/v1/projects/${projectId}/${action}`, {
    method: "POST",
    body: input,
  });
  return envelope.data;
}

export async function listAgentProfiles(): Promise<AgentProfileRecord[]> {
  const envelope = await request<AgentProfileRecord[]>("/api/v1/config/agents");
  return envelope.data;
}

export async function listSkillCatalog(): Promise<SkillCatalogRecord[]> {
  const envelope = await request<SkillCatalogRecord[]>("/api/v1/config/skills/catalog");
  return envelope.data;
}

export async function listSkillBindings(): Promise<SkillBindingRecord[]> {
  const envelope = await request<SkillBindingRecord[]>("/api/v1/config/skills");
  return envelope.data;
}

export async function listLLMStatus(): Promise<LLMStatusRecord[]> {
  const envelope = await request<LLMStatusRecord[]>("/api/v1/config/llms/status");
  return envelope.data;
}

export function paperPdfUrl(paper: PaperRecord): string {
  if (paper.source_pdf_is_real) {
    return `${API_BASE_URL}/api/v1/papers/${paper.paper_id}/pdf`;
  }
  return paper.pdf_url;
}

export function paperNoteUrl(paper: PaperRecord): string {
  return `${API_BASE_URL}/api/v1/papers/${paper.paper_id}/note/raw`;
}

export function paperRefinedUrl(paper: PaperRecord): string {
  return `${API_BASE_URL}/api/v1/papers/${paper.paper_id}/parsed/refined/raw`;
}

export async function importPaper(input: {
  mode: PaperResolveMode;
  value: string;
  categoryId?: number | null;
}): Promise<PaperRecord> {
  const resolution = await resolvePaper(input);
  const sourceUrl =
    resolution.landing_url ||
    (input.mode === "source_url" ? input.value : resolution.raw_input);
  const pdfUrl = resolution.pdf_url || resolution.final_url;
  const resolvedYear = Number.parseInt(resolution.year, 10);

  const paper = await createPaper({
    title: resolution.title || input.value,
    authors: resolution.authors,
    year: Number.isFinite(resolvedYear) ? resolvedYear : null,
    venue: resolution.venue,
    venue_short: resolution.venue,
    ccf_rank: resolution.ccf_rank,
    sci_quartile: resolution.sci_quartile,
    doi: resolution.doi,
    source_url: sourceUrl,
    pdf_url: pdfUrl,
    source_kind: "manual",
    category_id: input.categoryId ?? null,
  });

  const pipeline = await runPaperPipeline(paper.paper_id, {
    download_pdf: true,
    parse: true,
    refine_parse: true,
    split_sections: false,
    generate_note: false,
    require_review_confirmation: true,
  });
  return pipeline.paper;
}
