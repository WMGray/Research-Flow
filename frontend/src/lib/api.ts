import {
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
import {
  createCategory,
  deleteCategory,
  listCategories,
  type CategoryRecord,
} from "@/lib/categories";
import {
  confirmPaperReview,
  createPaper,
  getPaper,
  importPaper,
  listPapers,
  paperNoteUrl,
  paperPdfUrl,
  paperRefinedUrl,
  resolvePaper,
  retryPaperPipeline,
  runPaperAction,
  runPaperPipeline,
  startPaperImportPipeline,
  updatePaper,
  type PaperConfirmPipelineResponse,
  type PaperCreateInput,
  type PaperImportPipelineResponse,
  type PaperListResponse,
  type PaperPipelineResponse,
  type PaperRecord,
  type PaperResolveMode,
  type PaperResolveResponse,
  type PaperUpdateInput,
} from "@/lib/papers";

export {
  APIError,
  cancelJob,
  confirmPaperReview,
  createCategory,
  createPaper,
  deleteCategory,
  getPaper,
  getJob,
  importPaper,
  listCategories,
  listPapers,
  listJobs,
  paperNoteUrl,
  paperPdfUrl,
  paperRefinedUrl,
  resolvePaper,
  retryPaperPipeline,
  runPaperAction,
  runPaperPipeline,
  startPaperImportPipeline,
  updatePaper,
};
export type {
  APIEnvelope,
  CategoryRecord,
  JobListResponse,
  JobRecord,
  PaperConfirmPipelineResponse,
  PaperCreateInput,
  PaperImportPipelineResponse,
  PaperListResponse,
  PaperPipelineResponse,
  PaperRecord,
  PaperResolveMode,
  PaperResolveResponse,
  PaperUpdateInput,
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
