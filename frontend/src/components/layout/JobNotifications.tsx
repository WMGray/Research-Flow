import { useEffect, useMemo, useState } from "react";
import {
  APIError,
  cancelJob,
  listJobs,
  type JobRecord,
} from "@/lib/api";

const FINAL_JOB_STATUSES = new Set(["succeeded", "failed", "cancelled"]);
const LIVE_JOB_STATUSES = new Set(["queued", "running"]);

const jobTypeLabels: Record<string, string> = {
  paper_download: "Download",
  paper_parse: "Parse",
  paper_refine_parse: "Refine",
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

  async function loadJobs(showLoading = false): Promise<void> {
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
  }

  useEffect(() => {
    void loadJobs(true);
    const interval = window.setInterval(() => {
      void loadJobs(false);
    }, 5000);
    return () => window.clearInterval(interval);
  }, []);

  const liveCount = useMemo(
    () => jobs.filter((job) => LIVE_JOB_STATUSES.has(job.status)).length,
    [jobs],
  );
  const failedCount = useMemo(
    () => jobs.filter((job) => job.status === "failed").length,
    [jobs],
  );
  const badgeCount = liveCount + failedCount;

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
          <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-error px-1 text-[10px] font-bold leading-none text-white">
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
              jobs.map((job) => (
                <JobNotificationItem
                  isCancelling={cancellingJobId === job.job_id}
                  job={job}
                  key={job.job_id}
                  onCancel={() => void handleCancel(job)}
                />
              ))
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

  return (
    <article className="rounded-lg px-3 py-3 transition-colors hover:bg-surface-container-low">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-on-surface">{label}</p>
          <p className="mt-1 line-clamp-2 text-xs text-on-surface-variant">
            {job.error?.message || job.message || job.job_id}
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
        ) : null}
      </div>
    </article>
  );
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
