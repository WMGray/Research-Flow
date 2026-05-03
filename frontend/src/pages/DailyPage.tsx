import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  type FeedItemRecord,
  listFeedItems,
  refreshFeed,
  updateFeedItem,
} from "@/lib/api";

const dateLabel = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "2-digit",
  year: "numeric",
}).format(new Date());

const arxivCategories = ["cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.RO"];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export const DailyPage: React.FC = () => {
  const [feedDate, setFeedDate] = useState(today());
  const [query, setQuery] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<string[]>(arxivCategories);
  const [items, setItems] = useState<FeedItemRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadItems(): Promise<void> {
      setLoading(true);
      setError("");
      try {
        const response = await listFeedItems({
          feedDate,
          q: query,
          pageSize: 24,
        });
        if (!controller.signal.aborted) {
          setItems(response.items);
          setTotal(response.total);
        }
      } catch (exc) {
        if (!controller.signal.aborted) {
          setError(exc instanceof Error ? exc.message : "Failed to load feed items.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    const timer = window.setTimeout(() => void loadItems(), 180);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [feedDate, query]);

  async function handleRefresh(): Promise<void> {
    setRefreshing(true);
    setError("");
    try {
      const refreshed = await refreshFeed({
        feedDate,
        source: "arxiv",
        categories: selectedCategories,
        query,
        topic: selectedCategories.join(","),
        limit: 24,
      });
      setItems(refreshed);
      setTotal(refreshed.length);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to refresh feed.");
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }

  function toggleCategory(category: string): void {
    setSelectedCategories((current) =>
      current.includes(category)
        ? current.filter((item) => item !== category)
        : [...current, category],
    );
  }

  async function setItemStatus(
    item: FeedItemRecord,
    status: FeedItemRecord["status"],
  ): Promise<void> {
    setSavingId(item.item_id);
    setError("");
    try {
      const updated = await updateFeedItem(item.item_id, { status });
      setItems((current) =>
        current.map((entry) => (entry.item_id === updated.item_id ? updated : entry)),
      );
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to update feed item.");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        primaryActionIcon="refresh"
        primaryActionLabel={refreshing ? "Refreshing" : "Refresh Feed"}
        searchPlaceholder="Search daily feed by title, abstract, or topic..."
        searchValue={query}
        subtitle={dateLabel}
        title="Daily"
        onPrimaryAction={() => void handleRefresh()}
        onSearchChange={setQuery}
      />

      <main className="p-6 sm:p-8">
        <div className="mx-auto max-w-7xl space-y-8">
          <section className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
            <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
              <div>
                <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-primary">
                  Local feed
                </p>
                <h2 className="text-2xl font-black tracking-tight text-on-background">
                  Daily reading candidates generated from backend data
                </h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-on-surface-variant">
                  This feed is stored in SQLite and currently refreshes from imported papers.
                  It is ready for later arXiv/RSS ingestion without showing fake recommendations.
                </p>
              </div>
              <label className="block">
                <span className="mb-2 block text-xs font-bold text-on-surface-variant">
                  Feed date
                </span>
                <input
                  className="rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-2.5 text-sm outline-none transition focus:border-primary"
                  onChange={(event) => setFeedDate(event.target.value)}
                  type="date"
                  value={feedDate}
                />
              </label>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {arxivCategories.map((category) => (
                <button
                  className={`rounded-full px-3 py-1 text-[11px] font-bold transition ${
                    selectedCategories.includes(category)
                      ? "bg-primary text-on-primary"
                      : "bg-surface-container-high text-on-surface-variant"
                  }`}
                  key={category}
                  onClick={() => toggleCategory(category)}
                  type="button"
                >
                  {category}
                </button>
              ))}
            </div>
          </section>

          {error ? (
            <div className="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm font-medium text-error">
              {error}
            </div>
          ) : null}

          {loading ? (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
              {Array.from({ length: 8 }).map((_, index) => (
                <div
                  className="h-56 animate-pulse rounded-3xl bg-surface-container-low"
                  key={index}
                />
              ))}
            </div>
          ) : null}

          {!loading && items.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-outline-variant/30 bg-surface-container-lowest p-10 text-center shadow-sm">
              <span className="material-symbols-outlined text-5xl text-on-surface-variant/50">
                newspaper
              </span>
              <h3 className="mt-4 text-xl font-black text-on-surface">
                No feed items for this date
              </h3>
              <p className="mx-auto mt-2 max-w-xl text-sm text-on-surface-variant">
                Refresh the feed to generate candidates from stored papers, or import papers
                from Library first.
              </p>
              <div className="mt-6 flex justify-center gap-3">
                <button
                  className="rounded-xl bg-primary px-4 py-2 text-xs font-bold text-on-primary"
                  onClick={() => void handleRefresh()}
                  type="button"
                >
                  Refresh Feed
                </button>
                <Link
                  className="rounded-xl bg-surface-container-high px-4 py-2 text-xs font-bold text-on-surface"
                  to="/library"
                >
                  Go to Library
                </Link>
              </div>
            </div>
          ) : null}

          {!loading && items.length > 0 ? (
            <>
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-on-surface-variant">
                  {total} candidate items
                </p>
              </div>
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
                {items.map((item) => (
                  <FeedCard
                    item={item}
                    key={item.item_id}
                    onStatus={setItemStatus}
                    saving={savingId === item.item_id}
                  />
                ))}
              </div>
            </>
          ) : null}
        </div>
      </main>
    </div>
  );
};

function FeedCard({
  item,
  onStatus,
  saving,
}: {
  item: FeedItemRecord;
  onStatus: (item: FeedItemRecord, status: FeedItemRecord["status"]) => Promise<void>;
  saving: boolean;
}): React.ReactElement {
  return (
    <article className="group flex h-full flex-col rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm transition-all duration-300 hover:border-primary/20 hover:shadow-md">
      <div className="mb-3 flex items-start justify-between gap-3">
        <h3 className="pr-2 text-sm font-bold leading-tight text-on-surface line-clamp-2">
          {item.title}
        </h3>
        <span className="whitespace-nowrap rounded-md bg-primary/10 px-2 py-0.5 text-[10px] font-extrabold text-primary">
          {item.score}
        </span>
      </div>

      <p className="mb-3 text-[11px] font-bold uppercase tracking-widest text-on-surface-variant">
        {item.source} - {item.topic || item.status}
      </p>
      <p className="mb-4 text-[13px] leading-relaxed text-on-surface-variant line-clamp-4">
        {item.abstract || "No abstract recorded yet."}
      </p>
      <p className="mb-6 rounded-2xl bg-surface-container-low px-3 py-2 text-xs text-on-surface-variant line-clamp-3">
        {item.reason || "No ranking reason recorded."}
      </p>

      <div className="mt-auto flex flex-wrap gap-2 border-t border-surface-container/50 pt-4">
        {item.source_url ? (
          <a
            className="rounded-full bg-surface-container-high px-3 py-1 text-[11px] font-bold text-on-surface-variant hover:text-primary"
            href={item.source_url}
            rel="noreferrer"
            target="_blank"
          >
            arXiv
          </a>
        ) : null}
        {item.pdf_url ? (
          <a
            className="rounded-full bg-surface-container-high px-3 py-1 text-[11px] font-bold text-on-surface-variant hover:text-primary"
            href={item.pdf_url}
            rel="noreferrer"
            target="_blank"
          >
            PDF
          </a>
        ) : null}
        <FeedButton
          disabled={saving}
          label="Save"
          onClick={() => void onStatus(item, "saved")}
          selected={item.status === "saved"}
        />
        <FeedButton
          disabled={saving}
          label="Dismiss"
          onClick={() => void onStatus(item, "dismissed")}
          selected={item.status === "dismissed"}
        />
        <FeedButton
          disabled={saving}
          label="Candidate"
          onClick={() => void onStatus(item, "candidate")}
          selected={item.status === "candidate"}
        />
      </div>
    </article>
  );
}

function FeedButton({
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
