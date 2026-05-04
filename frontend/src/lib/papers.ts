import { API_BASE_URL, request } from "@/lib/http";
import { getJob, type JobRecord } from "@/lib/jobs";

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

export type PaperPipelineResponse = {
  paper_id: number;
  status: "succeeded" | "failed" | "waiting_review";
  message: string;
  stopped_at: string | null;
  jobs: JobRecord[];
  paper: PaperRecord;
};

export type PaperConfirmPipelineResponse = {
  paper: PaperRecord;
  job: JobRecord;
};

export type PaperImportPipelineResponse = {
  paper: PaperRecord;
  job: JobRecord;
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

export async function getPaper(paperId: number): Promise<PaperRecord> {
  const envelope = await request<PaperRecord>(`/api/v1/papers/${paperId}`);
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

export async function startPaperImportPipeline(
  paperId: number,
): Promise<PaperImportPipelineResponse> {
  const envelope = await request<PaperImportPipelineResponse>(
    `/api/v1/papers/${paperId}/import-pipeline`,
    { method: "POST" },
  );
  return envelope.data;
}

export async function retryPaperPipeline(
  paperId: number,
): Promise<PaperImportPipelineResponse> {
  const envelope = await request<PaperImportPipelineResponse>(
    `/api/v1/papers/${paperId}/retry-pipeline`,
    { method: "POST" },
  );
  return envelope.data;
}

export async function confirmPaperReview(
  paperId: number,
): Promise<PaperConfirmPipelineResponse> {
  const envelope = await request<PaperConfirmPipelineResponse>(
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
  const paper = await createPaper({
    title: input.value,
    source_url: input.mode === "source_url" ? input.value : "",
    doi: input.mode === "doi" ? input.value : "",
    pdf_url:
      input.mode === "source_url" && input.value.includes("/pdf/")
        ? input.value
        : "",
    source_kind: "search",
    category_id: input.categoryId ?? null,
  });

  const pipeline = await startPaperImportPipeline(paper.paper_id);
  return waitForPaperImport(pipeline.paper, pipeline.job.job_id);
}

const IMPORT_POLL_INTERVAL_MS = 1500;
const IMPORT_POLL_TIMEOUT_MS = 120000;
const FINAL_JOB_STATUSES = new Set([
  "succeeded",
  "failed",
  "cancelled",
  "waiting_review",
]);

async function waitForPaperImport(
  initialPaper: PaperRecord,
  jobId: string,
): Promise<PaperRecord> {
  const deadline = Date.now() + IMPORT_POLL_TIMEOUT_MS;
  let latestPaper = initialPaper;

  while (Date.now() < deadline) {
    const [paper, job] = await Promise.all([
      getPaper(initialPaper.paper_id),
      getJob(jobId),
    ]);
    latestPaper = paper;

    if (FINAL_JOB_STATUSES.has(job.status)) {
      return paper;
    }
    await delay(IMPORT_POLL_INTERVAL_MS);
  }

  return latestPaper;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
