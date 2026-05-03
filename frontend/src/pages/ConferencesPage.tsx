import React, { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  type ConferenceRecord,
  createConference,
  listConferences,
  updateConference,
} from "@/lib/api";

const statusOptions: Array<ConferenceRecord["status"]> = [
  "tracking",
  "submitted",
  "accepted",
  "rejected",
  "archived",
];

export const ConferencesPage: React.FC = () => {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<ConferenceRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadConferences(): Promise<void> {
      setLoading(true);
      setError("");
      try {
        const response = await listConferences({ q: query, pageSize: 50 });
        if (!controller.signal.aborted) {
          setItems(response.conferences);
          setTotal(response.total);
        }
      } catch (exc) {
        if (!controller.signal.aborted) {
          setError(exc instanceof Error ? exc.message : "Failed to load conferences.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    const timer = window.setTimeout(() => void loadConferences(), 180);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query]);

  async function addConference(): Promise<void> {
    setError("");
    try {
      const next = await createConference({
        name: "New Conference",
        acronym: `CONF${Date.now().toString().slice(-4)}`,
        year: new Date().getFullYear(),
        rank: "TBD",
        field: "Research",
        status: "tracking",
      });
      setItems((current) => [next, ...current]);
      setTotal((value) => value + 1);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to create conference.");
    }
  }

  async function setStatus(
    item: ConferenceRecord,
    status: ConferenceRecord["status"],
  ): Promise<void> {
    setSavingId(item.conference_id);
    setError("");
    try {
      const updated = await updateConference(item.conference_id, { status });
      setItems((current) =>
        current.map((entry) =>
          entry.conference_id === updated.conference_id ? updated : entry,
        ),
      );
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to update conference.");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        primaryActionIcon="add"
        primaryActionLabel="Track Venue"
        searchPlaceholder="Search venues, acronyms, or fields..."
        searchValue={query}
        subtitle={`${total} venues`}
        title="Conferences"
        onPrimaryAction={() => void addConference()}
        onSearchChange={setQuery}
      />
      <main className="p-6 sm:p-8">
        <div className="mx-auto max-w-7xl space-y-6">
          {error ? (
            <div className="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm font-medium text-error">
              {error}
            </div>
          ) : null}

          {loading ? (
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div className="h-56 animate-pulse rounded-3xl bg-surface-container-low" key={index} />
              ))}
            </div>
          ) : null}

          {!loading && items.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-outline-variant/30 bg-surface-container-lowest p-10 text-center shadow-sm">
              <span className="material-symbols-outlined text-5xl text-on-surface-variant/50">
                event_busy
              </span>
              <h3 className="mt-4 text-xl font-black text-on-surface">
                No conferences tracked
              </h3>
              <p className="mx-auto mt-2 max-w-xl text-sm text-on-surface-variant">
                Add a venue or clear search filters. Seeded top-tier venues are created by the
                backend on first use.
              </p>
            </div>
          ) : null}

          {!loading && items.length > 0 ? (
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {items.map((item) => (
                <ConferenceCard
                  item={item}
                  key={item.conference_id}
                  onStatus={setStatus}
                  saving={savingId === item.conference_id}
                />
              ))}
            </div>
          ) : null}
        </div>
      </main>
    </div>
  );
};

function ConferenceCard({
  item,
  onStatus,
  saving,
}: {
  item: ConferenceRecord;
  onStatus: (
    item: ConferenceRecord,
    status: ConferenceRecord["status"],
  ) => Promise<void>;
  saving: boolean;
}): React.ReactElement {
  return (
    <article className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-2xl font-black text-on-surface">{item.acronym}</h3>
          <p className="mt-1 text-sm font-semibold text-on-surface-variant">
            {item.name} {item.year}
          </p>
        </div>
        <span className="rounded-full bg-primary/10 px-3 py-1 text-[11px] font-bold text-primary">
          {item.rank || "TBD"}
        </span>
      </div>
      <div className="space-y-3 text-sm text-on-surface-variant">
        <Info label="Field" value={item.field || "Unspecified"} />
        <Info label="Abstract" value={item.abstract_deadline || "TBD"} />
        <Info label="Paper" value={item.paper_deadline || "TBD"} />
        <Info label="Notification" value={item.notification_date || "TBD"} />
      </div>
      <div className="mt-5 flex flex-wrap gap-2 border-t border-surface-container pt-4">
        {statusOptions.map((status) => (
          <button
            className={`rounded-full px-3 py-1 text-[11px] font-bold transition ${
              item.status === status
                ? "bg-primary text-on-primary"
                : "bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest"
            } disabled:cursor-not-allowed disabled:opacity-50`}
            disabled={saving}
            key={status}
            onClick={() => void onStatus(item, status)}
            type="button"
          >
            {status}
          </button>
        ))}
      </div>
    </article>
  );
}

function Info({ label, value }: { label: string; value: string }): React.ReactElement {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-xs font-bold uppercase tracking-widest">{label}</span>
      <span className="text-right text-sm font-semibold text-on-surface">{value}</span>
    </div>
  );
}
