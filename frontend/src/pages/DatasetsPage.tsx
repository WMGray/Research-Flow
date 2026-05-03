import React, { useCallback, useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  APIError,
  createDataset,
  listDatasets,
  type DatasetCreateInput,
  type DatasetRecord,
} from "@/lib/api";

const datasetsDateLabel = new Intl.DateTimeFormat("en-US", {
  weekday: "long",
  month: "long",
  day: "2-digit",
  year: "numeric",
}).format(new Date());

const emptyForm: DatasetCreateInput = {
  name: "",
  task_type: "",
  data_domain: "",
  scale: "",
  source: "manual",
  description: "",
  benchmark_summary: "",
  access_url: "",
};

export const DatasetsPage: React.FC = () => {
  const [datasets, setDatasets] = useState<DatasetRecord[]>([]);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const loadDatasets = useCallback(async (nextQuery = query): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await listDatasets({ q: nextQuery, pageSize: 50 });
      setDatasets(response.datasets);
      setSelectedId((currentId) => {
        if (currentId && response.datasets.some((item) => item.dataset_id === currentId)) {
          return currentId;
        }
        return response.datasets[0]?.dataset_id ?? null;
      });
      setError("");
    } catch (err) {
      setError(formatError(err));
    } finally {
      setIsLoading(false);
    }
  }, [query]);

  useEffect(() => {
    void loadDatasets("");
  }, [loadDatasets]);

  const selectedDataset = useMemo(
    () => datasets.find((dataset) => dataset.dataset_id === selectedId) ?? null,
    [datasets, selectedId],
  );

  const extractedCount = useMemo(
    () => datasets.filter((dataset) => dataset.source.includes("paper_extract")).length,
    [datasets],
  );

  async function handleCreate(input: DatasetCreateInput): Promise<void> {
    setIsSubmitting(true);
    try {
      const created = await createDataset(input);
      setDatasets((current) => [created, ...current]);
      setSelectedId(created.dataset_id);
      setIsCreateOpen(false);
      setError("");
    } catch (err) {
      setError(formatError(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        onPrimaryAction={() => setIsCreateOpen(true)}
        onSearchChange={setQuery}
        onSearchSubmit={() => void loadDatasets(query)}
        primaryActionIcon="add_circle"
        primaryActionLabel="New Dataset"
        searchPlaceholder="Search datasets, benchmarks, or domains..."
        searchValue={query}
        subtitle={datasetsDateLabel}
        title="Datasets"
      />

      <main className="grid gap-6 p-6 sm:p-8 xl:grid-cols-[22rem_minmax(0,1fr)]">
        <aside className="rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.22em] text-on-surface-variant">
                Dataset Registry
              </p>
              <p className="mt-1 text-xs text-on-surface-variant">
                {datasets.length} loaded, {extractedCount} extracted from papers
              </p>
            </div>
            <button
              className="rounded-lg px-2 py-1 text-xs font-bold text-primary hover:bg-primary/10"
              onClick={() => void loadDatasets(query)}
              type="button"
            >
              Refresh
            </button>
          </div>

          {error ? (
            <div className="mb-3 rounded-lg border border-error/20 bg-red-50 px-3 py-2 text-sm font-semibold text-error">
              {error}
            </div>
          ) : null}

          <div className="space-y-2">
            {isLoading ? (
              <DatasetListSkeleton />
            ) : datasets.length ? (
              datasets.map((dataset) => (
                <button
                  className={`w-full rounded-xl px-3 py-3 text-left transition-colors ${
                    dataset.dataset_id === selectedId
                      ? "bg-primary text-on-primary"
                      : "bg-surface-container-low text-on-surface hover:bg-surface-container"
                  }`}
                  key={dataset.dataset_id}
                  onClick={() => setSelectedId(dataset.dataset_id)}
                  type="button"
                >
                  <span className="line-clamp-1 text-sm font-bold">
                    {dataset.name}
                  </span>
                  <span
                    className={`mt-1 block line-clamp-1 text-xs ${
                      dataset.dataset_id === selectedId
                        ? "text-on-primary/80"
                        : "text-on-surface-variant"
                    }`}
                  >
                    {dataset.task_type || "Unspecified task"} ·{" "}
                    {dataset.data_domain || "No domain"}
                  </span>
                </button>
              ))
            ) : (
              <EmptyDatasetState hasQuery={Boolean(query.trim())} />
            )}
          </div>
        </aside>

        <section className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard label="Total Datasets" value={datasets.length} />
            <MetricCard label="Paper Extracted" value={extractedCount} />
            <MetricCard
              label="Domains"
              value={
                new Set(datasets.map((dataset) => dataset.data_domain).filter(Boolean))
                  .size
              }
            />
          </div>

          {selectedDataset ? (
            <DatasetDetail dataset={selectedDataset} />
          ) : (
            <div className="flex min-h-[360px] flex-col items-center justify-center rounded-2xl border border-dashed border-outline-variant/40 bg-surface-container-lowest p-8 text-center">
              <span className="material-symbols-outlined text-4xl text-on-surface-variant">
                database
              </span>
              <h2 className="mt-3 text-lg font-extrabold text-on-surface">
                No dataset selected
              </h2>
              <p className="mt-2 max-w-md text-sm text-on-surface-variant">
                Create a dataset manually or extract datasets from reviewed papers.
              </p>
            </div>
          )}
        </section>
      </main>

      {isCreateOpen ? (
        <CreateDatasetDialog
          isSubmitting={isSubmitting}
          onClose={() => setIsCreateOpen(false)}
          onSubmit={handleCreate}
        />
      ) : null}
    </div>
  );
};

function DatasetDetail({ dataset }: { dataset: DatasetRecord }) {
  return (
    <article className="overflow-hidden rounded-2xl border border-outline-variant/10 bg-surface-container-lowest shadow-sm">
      <div className="bg-gradient-to-br from-surface-container-low via-surface-container-lowest to-primary/10 p-6 sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-primary">
              Dataset Detail
            </p>
            <h2 className="mt-3 max-w-4xl text-3xl font-extrabold tracking-tight text-on-surface">
              {dataset.name}
            </h2>
            <div className="mt-4 flex flex-wrap gap-2">
              <Tag label={dataset.task_type || "task unspecified"} />
              <Tag label={dataset.data_domain || "domain unspecified"} />
              <Tag label={dataset.source || "source unspecified"} />
              {dataset.scale ? <Tag label={dataset.scale} /> : null}
            </div>
          </div>
          {dataset.access_url ? (
            <a
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-bold text-on-primary shadow-sm"
              href={dataset.access_url}
              rel="noreferrer"
              target="_blank"
            >
              <span className="material-symbols-outlined text-lg">open_in_new</span>
              Access
            </a>
          ) : null}
        </div>
      </div>

      <div className="grid gap-6 p-6 sm:p-8 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-6">
          <InfoBlock
            emptyText="No description has been recorded yet."
            label="Description"
            value={dataset.description}
          />
          <InfoBlock
            emptyText="No benchmark evidence has been recorded yet."
            label="Benchmark Summary / Evidence"
            value={dataset.benchmark_summary}
          />
        </div>

        <aside className="rounded-2xl bg-surface-container-low p-5">
          <h3 className="text-sm font-extrabold text-on-surface">Metadata</h3>
          <dl className="mt-4 space-y-3 text-sm">
            <MetaRow label="Dataset ID" value={String(dataset.dataset_id)} />
            <MetaRow label="Normalized" value={dataset.normalized_name || "-"} />
            <MetaRow
              label="Aliases"
              value={dataset.aliases.length ? dataset.aliases.join(", ") : "-"}
            />
            <MetaRow label="Updated" value={formatDate(dataset.updated_at)} />
          </dl>
        </aside>
      </div>
    </article>
  );
}

function CreateDatasetDialog({
  isSubmitting,
  onClose,
  onSubmit,
}: {
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (input: DatasetCreateInput) => Promise<void>;
}) {
  const [form, setForm] = useState<DatasetCreateInput>(emptyForm);

  function updateField(field: keyof DatasetCreateInput, value: string): void {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-on-background/35 px-4 py-8 backdrop-blur-sm">
      <div className="max-h-full w-full max-w-2xl overflow-y-auto rounded-2xl bg-surface-container-lowest p-6 shadow-[0_24px_80px_rgba(22,32,34,0.24)]">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-extrabold text-on-surface">
              Create Dataset
            </h2>
            <p className="mt-1 text-sm text-on-surface-variant">
              Add a benchmark or reusable dataset to the resource registry.
            </p>
          </div>
          <button
            className="flex h-9 w-9 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-surface-container"
            disabled={isSubmitting}
            onClick={onClose}
            type="button"
          >
            <span className="material-symbols-outlined text-xl">close</span>
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Field
            label="Name"
            onChange={(value) => updateField("name", value)}
            placeholder="MMLU"
            required
            value={form.name ?? ""}
          />
          <Field
            label="Task Type"
            onChange={(value) => updateField("task_type", value)}
            placeholder="reasoning_benchmark"
            value={form.task_type ?? ""}
          />
          <Field
            label="Domain"
            onChange={(value) => updateField("data_domain", value)}
            placeholder="nlp"
            value={form.data_domain ?? ""}
          />
          <Field
            label="Scale"
            onChange={(value) => updateField("scale", value)}
            placeholder="large"
            value={form.scale ?? ""}
          />
          <Field
            label="Source"
            onChange={(value) => updateField("source", value)}
            placeholder="manual"
            value={form.source ?? ""}
          />
          <Field
            label="Access URL"
            onChange={(value) => updateField("access_url", value)}
            placeholder="https://..."
            value={form.access_url ?? ""}
          />
        </div>

        <TextArea
          label="Description"
          onChange={(value) => updateField("description", value)}
          placeholder="What this dataset measures and when to use it."
          value={form.description ?? ""}
        />
        <TextArea
          label="Benchmark Summary"
          onChange={(value) => updateField("benchmark_summary", value)}
          placeholder="Evidence, metrics, or paper-derived context."
          value={form.benchmark_summary ?? ""}
        />

        <div className="mt-6 flex justify-end gap-3">
          <button
            className="h-10 rounded-lg px-4 text-sm font-semibold text-on-surface-variant transition-colors hover:bg-surface-container"
            disabled={isSubmitting}
            onClick={onClose}
            type="button"
          >
            Cancel
          </button>
          <button
            className="flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-on-primary shadow-sm disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!form.name?.trim() || isSubmitting}
            onClick={() => void onSubmit(form)}
            type="button"
          >
            <span className="material-symbols-outlined text-lg">
              {isSubmitting ? "progress_activity" : "database"}
            </span>
            <span>{isSubmitting ? "Creating..." : "Create Dataset"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  onChange,
  placeholder,
  required = false,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  placeholder: string;
  required?: boolean;
  value: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-on-surface-variant">
        {label}
        {required ? " *" : ""}
      </span>
      <input
        className="w-full rounded-lg border border-outline-variant/40 bg-surface-container-lowest px-3 py-3 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type="text"
        value={value}
      />
    </label>
  );
}

function TextArea({
  label,
  onChange,
  placeholder,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  placeholder: string;
  value: string;
}) {
  return (
    <label className="mt-4 block">
      <span className="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-on-surface-variant">
        {label}
      </span>
      <textarea
        className="min-h-24 w-full rounded-lg border border-outline-variant/40 bg-surface-container-lowest px-3 py-3 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-on-surface-variant">
        {label}
      </p>
      <p className="mt-2 text-3xl font-extrabold text-on-surface">{value}</p>
    </div>
  );
}

function InfoBlock({
  emptyText,
  label,
  value,
}: {
  emptyText: string;
  label: string;
  value: string;
}) {
  return (
    <section>
      <h3 className="text-sm font-extrabold text-on-surface">{label}</h3>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-on-surface-variant">
        {value || emptyText}
      </p>
    </section>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-outline-variant/10 pb-2">
      <dt className="text-on-surface-variant">{label}</dt>
      <dd className="max-w-[12rem] truncate text-right font-semibold text-on-surface">
        {value}
      </dd>
    </div>
  );
}

function Tag({ label }: { label: string }) {
  return (
    <span className="rounded-full bg-surface-container-high px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-on-surface">
      {label}
    </span>
  );
}

function DatasetListSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, index) => (
        <div
          className="h-[68px] animate-pulse rounded-xl bg-surface-container-low"
          key={index}
        />
      ))}
    </div>
  );
}

function EmptyDatasetState({ hasQuery }: { hasQuery: boolean }) {
  return (
    <div className="rounded-xl border border-dashed border-outline-variant/40 p-6 text-center">
      <span className="material-symbols-outlined text-3xl text-on-surface-variant">
        database
      </span>
      <p className="mt-2 text-sm font-bold text-on-surface">
        {hasQuery ? "No matching datasets" : "No datasets yet"}
      </p>
      <p className="mt-1 text-xs text-on-surface-variant">
        {hasQuery
          ? "Try another query."
          : "Create one manually or extract datasets from papers."}
      </p>
    </div>
  );
}

function formatDate(value: string): string {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

function formatError(err: unknown): string {
  if (err instanceof APIError) {
    return `${err.code}: ${err.message}`;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Unexpected dataset API error.";
}
