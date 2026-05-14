import { getJson } from "@/lib/http";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export type PaperRecord = {
  paper_id: string;
  title: string;
  slug: string;
  stage: string;
  status: string;
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
  error: string;
  updated_at: string;
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

export type HomeDashboardPayload = {
  ok: boolean;
  data: {
    totals: {
      papers: number;
      batches: number;
      processed: number;
      curated: number;
      library: number;
      needs_pdf: number;
      needs_review: number;
      failed: number;
    };
    status_counts: Record<string, number>;
    recent_papers: PaperRecord[];
    queue_items: PaperRecord[];
    recent_batches: BatchRecord[];
    paths: {
      data_root: string;
      discover_root: string;
      acquire_root: string;
      library_root: string;
    };
  };
  error: string | null;
};

export function fetchHomeDashboard(): Promise<HomeDashboardPayload> {
  return getJson<HomeDashboardPayload>(`${API_BASE_URL}/api/dashboard/home`);
}
