import { getJson, patchJson, postJson } from "@/lib/http";

const rawApiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "/").trim();
const API_BASE_URL = rawApiBaseUrl === "/" ? "" : rawApiBaseUrl.replace(/\/$/, "");

export type APIEnvelope<T> = {
  ok: boolean;
  data: T;
  error: string | null;
};

export type PaperRecord = {
  paper_id: string;
  title: string;
  slug: string;
  stage: string;
  status: string;
  workflow_status: string;
  asset_status: string;
  review_status: string;
  domain: string;
  area: string;
  topic: string;
  year: number | null;
  venue: string;
  doi: string;
  tags: string[];
  path: string;
  paper_path: string;
  note_path: string;
  refined_path: string;
  images_path: string;
  metadata_path: string;
  metadata_json_path: string;
  state_path: string;
  events_path: string;
  parsed_text_path: string;
  parsed_sections_path: string;
  pdf_analysis_path: string;
  parser_status: string;
  note_status: string;
  note_review_status: string;
  parser_artifacts: {
    text_path: string;
    sections_path: string;
    refined_path: string;
  };
  capabilities: {
    parse: boolean;
    accept: boolean;
    generate_note: boolean;
    review_refined: boolean;
    review_note: boolean;
    delete: boolean;
  };
  read_status: string;
  refined_review_status: string;
  classification_status: string;
  rejected: boolean;
  error: string;
  updated_at: string;
};

export type PaperEventRecord = {
  timestamp: string;
  event: string;
  actor: string;
  result: string;
  message: string;
  technical_detail: string;
  next_action: string;
};

export type BatchRecord = {
  batch_id: string;
  title: string;
  candidate_total: number;
  keep_total: number;
  reject_total: number;
  review_status: string;
  path: string;
  updated_at: string;
};

export type CandidateRecord = {
  candidate_id: string;
  batch_id: string;
  title: string;
  authors: string[];
  year: number | null;
  venue: string;
  decision: string;
  source_type: string;
  collection_role: string;
  paper_type: string;
  quality: number;
  relevance: number;
  recommendation_reason: string;
  landing_status: string;
  result_path: string;
  updated_at: string;
};

export type ParserRunRecord = {
  run_id: string;
  paper_id: string;
  status: string;
  parser: string;
  source_pdf: string;
  refined_path: string;
  image_dir: string;
  text_path: string;
  sections_path: string;
  error: string;
  started_at: string;
  finished_at: string;
};

export type HomeDashboardData = {
  totals: Record<string, number>;
  status_counts: Record<string, number>;
  recent_papers: PaperRecord[];
  queue_items: PaperRecord[];
  recent_batches: BatchRecord[];
  paths: Record<string, string>;
};

export type DiscoverDashboardData = {
  summary: Record<string, number>;
  batches: BatchRecord[];
  candidates: CandidateRecord[];
};

export type AcquireDashboardData = {
  summary: Record<string, number>;
  queue: PaperRecord[];
};

export type LibraryDashboardData = {
  summary: Record<string, number>;
  papers: PaperRecord[];
  paths: {
    library_root: string;
  };
};

/*
TODO(coming-soon): Re-enable with fetchPaperList when a direct paper list
screen is restored.

export type PaperListData = {
  items: PaperRecord[];
  total: number;
};
*/

export type ParserRunsData = {
  items: ParserRunRecord[];
  total: number;
};

export type PaperEventsData = {
  items: PaperEventRecord[];
  total: number;
};

export type ReviewDecisionPayload = {
  decision: "approved" | "rejected";
  comment?: string;
};

export type UpdateClassificationPayload = {
  domain: string;
  area: string;
  topic: string;
  title?: string;
  venue?: string;
  year?: number | null;
  tags?: string[];
  status?: string;
  paper_path?: string;
  note_path?: string;
  refined_path?: string;
};

export type ConfigHealthData = {
  data_layout: string;
  data_root: string;
  write_policy: string;
  paths: Record<string, { path: string; exists: boolean; is_dir: boolean }>;
  parser: {
    mineru_sdk_available: boolean;
    mineru_token_configured: boolean;
  };
};

export function fetchHomeDashboard(): Promise<APIEnvelope<HomeDashboardData>> {
  return getJson<APIEnvelope<HomeDashboardData>>(`${API_BASE_URL}/api/dashboard/home`);
}

export function fetchDiscoverDashboard(): Promise<APIEnvelope<DiscoverDashboardData>> {
  return getJson<APIEnvelope<DiscoverDashboardData>>(`${API_BASE_URL}/api/dashboard/discover`);
}

export function fetchAcquireDashboard(): Promise<APIEnvelope<AcquireDashboardData>> {
  return getJson<APIEnvelope<AcquireDashboardData>>(`${API_BASE_URL}/api/dashboard/acquire`);
}

export function fetchLibraryDashboard(): Promise<APIEnvelope<LibraryDashboardData>> {
  return getJson<APIEnvelope<LibraryDashboardData>>(`${API_BASE_URL}/api/dashboard/library`);
}

/*
TODO(coming-soon): Re-enable when a generic paper list view uses
GET /api/papers directly. Current pages use dashboard-scoped payloads.

export function fetchPaperList(): Promise<APIEnvelope<PaperListData>> {
  return getJson<APIEnvelope<PaperListData>>(`${API_BASE_URL}/api/papers`);
}
*/

export function fetchPaper(paperId: string): Promise<APIEnvelope<PaperRecord>> {
  return getJson<APIEnvelope<PaperRecord>>(`${API_BASE_URL}/api/papers/${encodeURIComponent(paperId)}`);
}

export function fetchParserRuns(paperId: string): Promise<APIEnvelope<ParserRunsData>> {
  return getJson<APIEnvelope<ParserRunsData>>(`${API_BASE_URL}/api/papers/${encodeURIComponent(paperId)}/parser-runs`);
}

export function fetchPaperEvents(paperId: string): Promise<APIEnvelope<PaperEventsData>> {
  return getJson<APIEnvelope<PaperEventsData>>(`${API_BASE_URL}/api/papers/${encodeURIComponent(paperId)}/events`);
}

export function fetchConfigHealth(): Promise<APIEnvelope<ConfigHealthData>> {
  return getJson<APIEnvelope<ConfigHealthData>>(`${API_BASE_URL}/api/config`);
}

export function setCandidateDecision(batchId: string, candidateId: string, decision: string): Promise<APIEnvelope<CandidateRecord>> {
  return postJson<APIEnvelope<CandidateRecord>>(
    `${API_BASE_URL}/api/discover/batches/${encodeURIComponent(batchId)}/candidates/${encodeURIComponent(candidateId)}/decision`,
    { decision }
  );
}

export function parsePaperPdf(paperId: string, force = false): Promise<APIEnvelope<PaperRecord>> {
  return postJson<APIEnvelope<PaperRecord>>(`${API_BASE_URL}/api/papers/${encodeURIComponent(paperId)}/parse-pdf`, {
    force,
    parser: "mineru"
  });
}

export function acceptPaper(paperId: string): Promise<APIEnvelope<PaperRecord>> {
  return postJson<APIEnvelope<PaperRecord>>(`${API_BASE_URL}/api/papers/${encodeURIComponent(paperId)}/accept`, {});
}

export function updatePaperClassification(paperId: string, payload: UpdateClassificationPayload): Promise<APIEnvelope<PaperRecord>> {
  return patchJson<APIEnvelope<PaperRecord>>(`${API_BASE_URL}/api/papers/${encodeURIComponent(paperId)}/classification`, payload);
}

export function rejectPaper(paperId: string): Promise<APIEnvelope<PaperRecord>> {
  return postJson<APIEnvelope<PaperRecord>>(`${API_BASE_URL}/api/papers/${encodeURIComponent(paperId)}/reject`);
}

export function generatePaperNote(paperId: string, overwrite = false): Promise<APIEnvelope<PaperRecord>> {
  return postJson<APIEnvelope<PaperRecord>>(`${API_BASE_URL}/api/papers/${encodeURIComponent(paperId)}/generate-note`, {
    overwrite
  });
}

export function reviewPaperRefined(paperId: string, payload: ReviewDecisionPayload): Promise<APIEnvelope<PaperRecord>> {
  return postJson<APIEnvelope<PaperRecord>>(`${API_BASE_URL}/api/papers/${encodeURIComponent(paperId)}/review-refined`, payload);
}

export function reviewPaperNote(paperId: string, payload: ReviewDecisionPayload): Promise<APIEnvelope<PaperRecord>> {
  return postJson<APIEnvelope<PaperRecord>>(`${API_BASE_URL}/api/papers/${encodeURIComponent(paperId)}/review-note`, payload);
}
