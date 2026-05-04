import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  APIError,
  cancelJob,
  listJobs,
  type JobRecord,
} from "@/lib/api";

const FINAL_JOB_STATUSES = new Set(["succeeded", "failed", "cancelled"]);
const LIVE_JOB_STATUSES = new Set(["queued", "running"]);

const jobTypeLabels: Record<string, string> = {
  paper_resolve_metadata: "Metadata",
  paper_download: "Download",
  paper_parse: "Parse",
  paper_refine_parse: "Refine",
  paper_retry_pipeline: "Retry Pipeline",
  paper_import_pipeline: "Import Pipeline",
  paper_confirm_pipeline: "Review Confirm Pipeline",
  paper_split_sections: "Sections",
  paper_generate_note: "Note",
  paper_extract_knowledge: "Knowledge",
  paper_extract_datasets: "Datasets",
};

const statusLabels: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
};

export function JobNotifications() {
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [cancellingJobId, setCancellingJobId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const loadJobs = useCallback(async (showLoading = false): Promise<void> => {
    if (showLoading) {
      setIsLoading(true);
    }
    try {
      const response = await listJobs({ pageSize: 8 });
      setJobs(response.jobs);
      setError("");
    } catch (err) {
      setError(formatError(err));
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadJobs(true);
  }, [loadJobs]);

  const liveCount = useMemo(
    () => jobs.filter((job) => LIVE_JOB_STATUSES.has(job.status)).length,
    [jobs],
  );
  const failedCount = useMemo(
    () => jobs.filter((job) => job.status === "failed").length,
    [jobs],
  );
  const badgeCount = liveCount + failedCount;

  useEffect(() => {
    const pollInterval = liveCount || isOpen ? 4000 : 45000;
    const interval = window.setInterval(() => {
      if (document.visibilityState !== "visible") {
        return;
      }
      void loadJobs(false);
    }, pollInterval);
    return () => window.clearInterval(interval);
  }, [isOpen, liveCount, loadJobs]);

  const runningJobs = useMemo(
    () => jobs.filter((job) => LIVE_JOB_STATUSES.has(job.status)),
    [jobs],
  );
  const failedJobs = useMemo(
    () => jobs.filter((job) => job.status === "failed"),
    [jobs],
  );
  const recentJobs = useMemo(
    () =>
      jobs.filter(
        (job) => FINAL_JOB_STATUSES.has(job.status) && job.status !== "failed",
      ),
    [jobs],
  );

  async function handleCancel(job: JobRecord): Promise<void> {
    setCancellingJobId(job.job_id);
    try {
      const updated = await cancelJob(job.job_id);
      setJobs((currentJobs) =>
        currentJobs.map((currentJob) =>
          currentJob.job_id === updated.job_id ? updated : currentJob,
        ),
      );
      setError("");
    } catch (err) {
      setError(formatError(err));
    } finally {
      setCancellingJobId(null);
    }
  }

  return (
    <div className="relative">
      <button
        aria-expanded={isOpen}
        aria-label="Recent jobs"
        className="relative flex h-10 w-10 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-primary"
        onClick={() => {
          setIsOpen((current) => !current);
          void loadJobs(false);
        }}
        type="button"
      >
        <span className="material-symbols-outlined">
          {liveCount ? "sync" : "notifications"}
        </span>
        {badgeCount ? (
          <span
            className={`absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-bold leading-none text-white ${
              failedCount ? "bg-error" : "bg-primary"
            }`}
          >
            {badgeCount}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div className="absolute right-0 top-12 z-50 w-[min(360px,calc(100vw-2rem))] overflow-hidden rounded-xl border border-outline-variant/20 bg-surface-container-lowest shadow-[0_24px_80px_rgba(22,32,34,0.18)]">
          <div className="flex items-center justify-between border-b border-outline-variant/15 px-4 py-3">
            <div>
              <p className="text-sm font-extrabold text-on-surface">Recent Jobs</p>
              <p className="text-xs text-on-surface-variant">
                {liveCount ? `${liveCount} running or queued` : "No active jobs"}
              </p>
            </div>
            <button
              className="rounded-md px-2 py-1 text-xs font-bold text-primary hover:bg-primary/10 disabled:opacity-50"
              disabled={isLoading}
              onClick={() => void loadJobs(true)}
              type="button"
            >
              {isLoading ? "Refreshing" : "Refresh"}
            </button>
          </div>

          {error ? (
            <div className="m-3 rounded-lg border border-error/20 bg-red-50 px-3 py-2 text-xs font-semibold text-error">
              {error}
            </div>
          ) : null}

          <div className="max-h-[420px] overflow-y-auto p-2">
            {jobs.length ? (
              <div className="space-y-3">
                <JobGroup
                  emptyLabel="No running jobs"
                  isCancellingJobId={cancellingJobId}
                  jobs={runningJobs}
                  label="Running"
                  onCancel={handleCancel}
                />
                <JobGroup
                  emptyLabel="No failed jobs"
                  isCancellingJobId={cancellingJobId}
                  jobs={failedJobs}
                  label="Failed"
                  onCancel={handleCancel}
                />
                <JobGroup
                  emptyLabel="No completed jobs"
                  isCancellingJobId={cancellingJobId}
                  jobs={recentJobs}
                  label="Recently completed"
                  onCancel={handleCancel}
                />
              </div>
            ) : (
              <div className="flex min-h-28 flex-col items-center justify-center px-4 text-center">
                <span className="material-symbols-outlined text-2xl text-on-surface-variant">
                  task_alt
                </span>
                <p className="mt-2 text-sm font-bold text-on-surface">
                  No jobs yet
                </p>
                <p className="mt-1 text-xs text-on-surface-variant">
                  Imports and paper actions will appear here.
                </p>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function JobGroup({
  emptyLabel,
  isCancellingJobId,
  jobs,
  label,
  onCancel,
}: {
  emptyLabel: string;
  isCancellingJobId: string | null;
  jobs: JobRecord[];
  label: string;
  onCancel: (job: JobRecord) => Promise<void>;
}) {
  return (
    <section>
      <div className="mb-1 flex items-center justify-between px-1">
        <h3 className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-on-surface-variant">
          {label}
        </h3>
        <span className="text-[10px] font-bold text-on-surface-variant">
          {jobs.length}
        </span>
      </div>
      {jobs.length ? (
        <div className="space-y-1">
          {jobs.map((job) => (
            <JobNotificationItem
              isCancelling={isCancellingJobId === job.job_id}
              job={job}
              key={job.job_id}
              onCancel={() => void onCancel(job)}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg px-3 py-2 text-xs font-medium text-on-surface-variant">
          {emptyLabel}
        </div>
      )}
    </section>
  );
}

function JobNotificationItem({
  isCancelling,
  job,
  onCancel,
}: {
  isCancelling: boolean;
  job: JobRecord;
  onCancel: () => void;
}) {
  const canCancel = !FINAL_JOB_STATUSES.has(job.status);
  const statusClass = getStatusClass(job.status);
  const label = jobTypeLabels[job.type] ?? job.type;
  const resourceHref = getResourceHref(job);
  const resourceLabel = getResourceLabel(job);
  const message = formatJobMessage(job);

  return (
    <article
      className={`rounded-lg px-3 py-3 transition-colors hover:bg-surface-container-low ${
        job.status === "failed" ? "border border-error/20 bg-red-50" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-on-surface">
            {resourceLabel || label}
          </p>
          <p className="mt-1 text-[11px] font-bold uppercase tracking-[0.14em] text-on-surface-variant">
            {label}
          </p>
          <p className="mt-1 line-clamp-2 text-xs text-on-surface-variant">
            {message}
          </p>
          <p className="mt-1 truncate text-[10px] font-bold uppercase tracking-[0.14em] text-on-surface-variant">
            {getResourceMeta(job)} - {formatTime(job.updated_at)}
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${statusClass}`}
        >
          {statusLabels[job.status] ?? job.status}
        </span>
      </div>
      <div className="mt-3 flex items-center justify-between gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-container-high">
          <div
            className={`h-full rounded-full ${getProgressClass(job.status)}`}
            style={{ width: `${Math.max(4, Math.round(job.progress * 100))}%` }}
          />
        </div>
        {canCancel ? (
          <button
            className="text-xs font-bold text-error hover:underline disabled:opacity-50"
            disabled={isCancelling}
            onClick={onCancel}
            type="button"
          >
            {isCancelling ? "Cancelling" : "Cancel"}
          </button>
        ) : resourceHref ? (
          <Link
            className="text-xs font-bold text-primary hover:underline"
            aria-label={`View ${resourceLabel} ${job.type} ${formatTime(job.updated_at)}`}
            data-testid={`job-view-${job.job_id}`}
            to={resourceHref}
          >
            View
          </Link>
        ) : (
          <span className="text-xs font-bold text-on-surface-variant/60">
            No resource
          </span>
        )}
      </div>
    </article>
  );
}

function getResourceHref(job: JobRecord): string | null {
  if (!job.resource_id) {
    return null;
  }
  switch (job.resource_type) {
    case "paper":
      return `/library?paper_id=${job.resource_id}`;
    case "project":
      return `/projects?project_id=${job.resource_id}`;
    case "dataset":
      return `/datasets?dataset_id=${job.resource_id}`;
    case "knowledge":
      return `/views?knowledge_id=${job.resource_id}`;
    default:
      return null;
  }
}

function getResourceLabel(job: JobRecord): string {
  if (job.resource_label?.trim()) {
    return job.resource_label.trim();
  }
  if (!job.resource_type || !job.resource_id) {
    return "";
  }
  return `${job.resource_type} #${job.resource_id}`;
}

function getResourceMeta(job: JobRecord): string {
  if (!job.resource_type || !job.resource_id) {
    return "No linked resource";
  }
  return `${job.resource_type} #${job.resource_id}`;
}

function formatJobMessage(job: JobRecord): string {
  if (job.error?.message) {
    if (job.type === "paper_resolve_metadata") {
      return `Metadata refresh failed: ${job.error.message}`;
    }
    return job.error.message;
  }

  const message = (job.message || "").trim();
  if (!message) {
    return job.job_id;
  }

  if (job.type === "paper_retry_pipeline" && job.status === "waiting_review") {
    return "已完成 parse/refine，当前等待 refined.md 人工审核。";
  }
  if (job.type === "paper_retry_pipeline" && job.status === "running") {
    return "正在重跑导入链路，依次执行 metadata、download、parse、refine。";
  }
  if (job.type === "paper_import_pipeline" && job.status === "waiting_review") {
    return "导入链路已完成 parse/refine，当前等待 refined.md 人工审核。";
  }
  if (job.type === "paper_confirm_pipeline" && job.status === "running") {
    return "正在继续审核后的下游步骤，包括分节、笔记和抽取任务。";
  }
  if (message === "Import pipeline stopped for refined.md review.") {
    return "已完成 parse/refine，当前等待 refined.md 人工审核。";
  }
  if (message === "Prepared paper PDF for parsing.") {
    return "PDF 已就绪，准备进入 parse。";
  }
  if (message === "Parsed paper into raw markdown.") {
    return "已完成 PDF 解析，生成 raw markdown。";
  }
  if (message === "Refined parsed markdown.") {
    return "已完成 refined markdown 修复。";
  }
  if (message === "Resolved paper metadata.") {
    return "Metadata refreshed from resolver results.";
  }
  if (message === "Resolved paper metadata from arXiv.") {
    return "Metadata refreshed from arXiv.";
  }
  if (message === "Confirmed review and completed paper extraction pipeline.") {
    return "Review confirmed and downstream note/knowledge/dataset steps completed.";
  }
  if (message === "Generated canonical paper sections.") {
    return "Canonical paper sections generated.";
  }
  if (message === "Generated paper note.md from canonical sections.") {
    return "Paper note generated from canonical sections.";
  }
  if (message === "Extracted evidence-grounded knowledge from local paper text.") {
    return "Evidence-grounded knowledge extracted from the paper.";
  }
  if (message === "Extracted dataset mentions from local paper text.") {
    return "Dataset mentions extracted from the paper.";
  }
  return message;
}

function formatTime(value: string): string {
  if (!value) {
    return "unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getStatusClass(status: string): string {
  switch (status) {
    case "succeeded":
      return "bg-green-100 text-green-800";
    case "failed":
      return "bg-red-100 text-red-800";
    case "cancelled":
      return "bg-gray-100 text-gray-700";
    case "queued":
    case "running":
      return "bg-blue-100 text-blue-800";
    default:
      return "bg-surface-container-high text-on-surface-variant";
  }
}

function getProgressClass(status: string): string {
  if (status === "failed") {
    return "bg-error";
  }
  if (status === "succeeded") {
    return "bg-green-600";
  }
  if (status === "cancelled") {
    return "bg-gray-500";
  }
  return "bg-primary";
}

function formatError(err: unknown): string {
  if (err instanceof APIError) {
    return `${err.code}: ${err.message}`;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Unexpected job API error.";
}
