import React, { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  type KnowledgeRecord,
  listKnowledge,
  updateKnowledge,
} from "@/lib/api";

const typeOptions: Array<{ label: string; value: "" | KnowledgeRecord["knowledge_type"] }> = [
  { label: "All", value: "" },
  { label: "Views", value: "view" },
  { label: "Definitions", value: "definition" },
];

const reviewOptions: Array<{ label: string; value: "" | KnowledgeRecord["review_status"] }> = [
  { label: "All review states", value: "" },
  { label: "Pending", value: "pending_review" },
  { label: "Accepted", value: "accepted" },
  { label: "Rejected", value: "rejected" },
];

function confidenceLabel(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatDate(value: string): string {
  if (!value) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export const ViewsPage: React.FC = () => {
  const [query, setQuery] = useState("");
  const [knowledgeType, setKnowledgeType] = useState<"" | KnowledgeRecord["knowledge_type"]>("");
  const [reviewStatus, setReviewStatus] = useState<"" | KnowledgeRecord["review_status"]>("");
  const [items, setItems] = useState<KnowledgeRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadKnowledge(): Promise<void> {
      setLoading(true);
      setError("");
      try {
        const response = await listKnowledge({
          q: query,
          knowledgeType,
          reviewStatus,
          pageSize: 24,
        });
        setItems(response.knowledge);
        setTotal(response.total);
      } catch (exc) {
        if (!controller.signal.aborted) {
          setError(exc instanceof Error ? exc.message : "Failed to load knowledge.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    const timer = window.setTimeout(() => void loadKnowledge(), 180);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [knowledgeType, query, reviewStatus]);

  async function setReviewState(
    item: KnowledgeRecord,
    nextStatus: KnowledgeRecord["review_status"],
  ): Promise<void> {
    setSavingId(item.knowledge_id);
    setError("");
    try {
      const updated = await updateKnowledge(item.knowledge_id, {
        review_status: nextStatus,
      });
      setItems((current) =>
        current.map((entry) =>
          entry.knowledge_id === updated.knowledge_id ? updated : entry,
        ),
      );
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to update review state.");
    } finally {
      setSavingId(null);
    }
  }

  const acceptedCount = items.filter((item) => item.review_status === "accepted").length;
  const pendingCount = items.filter((item) => item.review_status === "pending_review").length;
  const fields = Array.from(
    new Set(items.map((item) => item.research_field || item.category_label).filter(Boolean)),
  ).slice(0, 10);

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        primaryActionIcon="psychology"
        primaryActionLabel="Extract From Paper"
        searchPlaceholder="Search insights, evidence, or source sections..."
        subtitle="Evidence-grounded synthesis"
        title="Views"
      />

      <main className="grid gap-8 p-6 sm:p-8 xl:grid-cols-[18rem_minmax(0,1fr)]">
        <aside className="space-y-5">
          <section className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm">
            <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-on-surface-variant">
              Filters
            </span>
            <label className="mt-4 block">
              <span className="mb-2 block text-xs font-bold text-on-surface-variant">
                Search
              </span>
              <input
                className="w-full rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-2.5 text-sm outline-none transition focus:border-primary"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="method, limitation, MMLU..."
                value={query}
              />
            </label>

            <div className="mt-5 space-y-2">
              {typeOptions.map((option) => (
                <button
                  className={`flex w-full items-center justify-between rounded-2xl px-4 py-3 text-left text-sm transition-colors ${
                    knowledgeType === option.value
                      ? "bg-primary/10 font-bold text-primary"
                      : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                  }`}
                  key={option.label}
                  onClick={() => setKnowledgeType(option.value)}
                  type="button"
                >
                  {option.label}
                </button>
              ))}
            </div>

            <label className="mt-5 block">
              <span className="mb-2 block text-xs font-bold text-on-surface-variant">
                Review state
              </span>
              <select
                className="w-full rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-2.5 text-sm outline-none transition focus:border-primary"
                onChange={(event) =>
                  setReviewStatus(event.target.value as "" | KnowledgeRecord["review_status"])
                }
                value={reviewStatus}
              >
                {reviewOptions.map((option) => (
                  <option key={option.label} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </section>

          <section className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm">
            <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-on-surface-variant">
              Loaded scope
            </span>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <Stat label="Total" value={total} />
              <Stat label="Accepted" value={acceptedCount} />
              <Stat label="Pending" value={pendingCount} />
              <Stat label="Fields" value={fields.length} />
            </div>
          </section>
        </aside>

        <section className="space-y-8">
          <header className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
            <h3 className="mb-2 text-2xl font-black tracking-tight text-on-surface">
              Knowledge extracted from papers
            </h3>
            <p className="max-w-3xl text-sm leading-6 text-on-surface-variant">
              This page now reads from `/api/v1/knowledge`. Each card keeps its evidence,
              source section, confidence, and human review state visible so the UI can support
              the manual refine and review loop instead of presenting static examples.
            </p>
            {fields.length > 0 ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {fields.map((field) => (
                  <span
                    className="rounded-full bg-primary/10 px-3 py-1 text-[11px] font-bold text-primary"
                    key={field}
                  >
                    {field}
                  </span>
                ))}
              </div>
            ) : null}
          </header>

          {error ? (
            <div className="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm font-medium text-error">
              {error}
            </div>
          ) : null}

          {loading ? (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 2xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div
                  className="h-64 animate-pulse rounded-3xl bg-surface-container-low"
                  key={index}
                />
              ))}
            </div>
          ) : null}

          {!loading && items.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-outline-variant/30 bg-surface-container-lowest p-8 text-center shadow-sm">
              <span className="material-symbols-outlined text-4xl text-on-surface-variant/50">
                travel_explore
              </span>
              <h4 className="mt-3 text-lg font-black text-on-surface">
                No knowledge records yet
              </h4>
              <p className="mx-auto mt-2 max-w-xl text-sm text-on-surface-variant">
                Run `extract-knowledge` from a refined paper or import a paper through the
                Library pipeline. The page intentionally shows an empty state rather than mock
                insights.
              </p>
            </div>
          ) : null}

          {!loading && items.length > 0 ? (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 2xl:grid-cols-3">
              {items.map((item) => (
                <KnowledgeCard
                  item={item}
                  key={item.knowledge_id}
                  onReview={setReviewState}
                  saving={savingId === item.knowledge_id}
                />
              ))}
            </div>
          ) : null}
        </section>
      </main>
    </div>
  );
};

function KnowledgeCard({
  item,
  onReview,
  saving,
}: {
  item: KnowledgeRecord;
  onReview: (
    item: KnowledgeRecord,
    nextStatus: KnowledgeRecord["review_status"],
  ) => Promise<void>;
  saving: boolean;
}): React.ReactElement {
  return (
    <article className="group flex min-h-[21rem] flex-col gap-4 rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm transition-all hover:border-primary/20 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <span
          className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold ${
            item.knowledge_type === "definition"
              ? "border-blue-100 bg-blue-50 text-blue-700"
              : "border-emerald-100 bg-emerald-50 text-emerald-700"
          }`}
        >
          {item.knowledge_type}
        </span>
        <span className="rounded-full bg-surface-container-high px-2.5 py-0.5 text-[10px] font-bold text-on-surface-variant">
          {confidenceLabel(item.confidence_score)}
        </span>
      </div>

      <h4 className="text-lg font-black leading-snug text-on-surface line-clamp-3">
        {item.title}
      </h4>
      <p className="text-sm leading-6 text-on-surface-variant line-clamp-4">
        {item.summary_zh || item.original_text_en || "No summary text recorded."}
      </p>

      <blockquote className="rounded-2xl bg-surface-container-low px-4 py-3 text-xs italic leading-5 text-on-surface-variant line-clamp-4">
        {item.evidence_text || "Evidence text is empty."}
      </blockquote>

      <footer className="mt-auto space-y-4 border-t border-surface-container pt-4">
        <div className="grid grid-cols-2 gap-3 text-[11px] text-on-surface-variant">
          <span>Section: {item.source_section || "Unknown"}</span>
          <span>Updated: {formatDate(item.updated_at)}</span>
          <span>Field: {item.research_field || item.category_label || "Unlabeled"}</span>
          <span>Status: {item.review_status}</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <ReviewButton
            disabled={saving}
            label="Accept"
            onClick={() => void onReview(item, "accepted")}
            selected={item.review_status === "accepted"}
          />
          <ReviewButton
            disabled={saving}
            label="Reject"
            onClick={() => void onReview(item, "rejected")}
            selected={item.review_status === "rejected"}
          />
          <ReviewButton
            disabled={saving}
            label="Pending"
            onClick={() => void onReview(item, "pending_review")}
            selected={item.review_status === "pending_review"}
          />
        </div>
      </footer>
    </article>
  );
}

function ReviewButton({
  disabled,
  label,
  onClick,
  selected,
}: {
  disabled: boolean;
  label: string;
  onClick: () => void;
  selected: boolean;
}): React.ReactElement {
  return (
    <button
      className={`rounded-full px-3 py-1 text-[11px] font-bold transition ${
        selected
          ? "bg-primary text-on-primary"
          : "bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest"
      } disabled:cursor-not-allowed disabled:opacity-50`}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}

function Stat({ label, value }: { label: string; value: number }): React.ReactElement {
  return (
    <div className="rounded-2xl bg-surface-container-low p-3">
      <p className="text-xl font-black text-on-surface">{value}</p>
      <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
        {label}
      </p>
    </div>
  );
}
