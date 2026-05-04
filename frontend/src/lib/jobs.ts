import { request } from "@/lib/http";

export type JobRecord = {
  job_id: string;
  type: string;
  status: string;
  progress: number;
  message: string;
  resource_type: string;
  resource_id: number;
  resource_label: string;
  created_at: string;
  updated_at: string;
  result: Record<string, unknown> | null;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

export type JobListResponse = {
  jobs: JobRecord[];
  total: number;
  page: number;
  pageSize: number;
};

export async function listJobs(input: {
  page?: number;
  pageSize?: number;
  resourceType?: string;
  resourceId?: number;
  status?: string;
} = {}): Promise<JobListResponse> {
  const params = new URLSearchParams();
  params.set("page", String(input.page ?? 1));
  params.set("page_size", String(input.pageSize ?? 10));
  if (input.resourceType) {
    params.set("resource_type", input.resourceType);
  }
  if (input.resourceId !== undefined) {
    params.set("resource_id", String(input.resourceId));
  }
  if (input.status) {
    params.set("status", input.status);
  }
  const envelope = await request<JobRecord[]>(`/api/v1/jobs?${params.toString()}`);
  return {
    jobs: envelope.data,
    total: Number(envelope.meta.total ?? envelope.data.length),
    page: Number(envelope.meta.page ?? input.page ?? 1),
    pageSize: Number(envelope.meta.page_size ?? input.pageSize ?? 10),
  };
}

export async function getJob(jobId: string): Promise<JobRecord> {
  const envelope = await request<JobRecord>(`/api/v1/jobs/${jobId}`);
  return envelope.data;
}

export async function cancelJob(jobId: string): Promise<JobRecord> {
  const envelope = await request<JobRecord>(`/api/v1/jobs/${jobId}/cancel`, {
    method: "POST",
  });
  return envelope.data;
}
