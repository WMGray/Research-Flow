import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  APIError,
  createProject,
  getProjectDocument,
  listProjects,
  runProjectAction,
  type ProjectCreateInput,
  type ProjectDocumentRecord,
  type ProjectRecord,
} from "@/lib/api";

const projectSections = [
  "overview",
  "related_work",
  "method",
  "experiment",
  "conclusion",
  "manuscript",
] as const;

const statusLabels: Record<ProjectRecord["status"], string> = {
  planning: "Planning",
  researching: "Researching",
  experimenting: "Experimenting",
  writing: "Writing",
  archived: "Archived",
};

export const ProjectsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [overview, setOverview] = useState<ProjectDocumentRecord | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRefreshingOverview, setIsRefreshingOverview] = useState(false);
  const [error, setError] = useState("");
  const focusedProjectId = Number.parseInt(searchParams.get("project_id") ?? "", 10);
  const focusedProjectRef = React.useRef<HTMLButtonElement | null>(null);

  const loadProjects = useCallback(async (nextQuery = query): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await listProjects({ q: nextQuery, pageSize: 50 });
      setProjects(response.projects);
      setSelectedId((currentId) => {
        if (currentId && response.projects.some((project) => project.project_id === currentId)) {
          return currentId;
        }
        return response.projects[0]?.project_id ?? null;
      });
      setError("");
    } catch (err) {
      setError(formatError(err));
    } finally {
      setIsLoading(false);
    }
  }, [query]);

  useEffect(() => {
    void loadProjects("");
  }, [loadProjects]);

  useEffect(() => {
    if (Number.isNaN(focusedProjectId) || focusedProjectId <= 0) {
      return;
    }
    setSelectedId(focusedProjectId);
  }, [focusedProjectId]);

  useEffect(() => {
    if (Number.isNaN(focusedProjectId) || focusedProjectId <= 0) {
      return;
    }
    focusedProjectRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }, [focusedProjectId, projects]);

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_id === selectedId) ?? null,
    [projects, selectedId],
  );

  useEffect(() => {
    if (!selectedProject) {
      setOverview(null);
      return;
    }
    let cancelled = false;
    getProjectDocument(selectedProject.project_id, "overview")
      .then((document) => {
        if (!cancelled) {
          setOverview(document);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setOverview(null);
          setError(formatError(err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedProject]);

  const statusCounts = useMemo(() => {
    return projects.reduce<Record<string, number>>((accumulator, project) => {
      accumulator[project.status] = (accumulator[project.status] ?? 0) + 1;
      return accumulator;
    }, {});
  }, [projects]);

  async function handleCreate(input: ProjectCreateInput): Promise<void> {
    setIsSubmitting(true);
    try {
      const created = await createProject(input);
      setProjects((current) => [created, ...current]);
      setSelectedId(created.project_id);
      setIsCreateOpen(false);
      setError("");
    } catch (err) {
      setError(formatError(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRefreshOverview(): Promise<void> {
    if (!selectedProject) {
      return;
    }
    setIsRefreshingOverview(true);
    try {
      const job = await runProjectAction(selectedProject.project_id, "refresh-overview");
      if (job.status !== "succeeded") {
        throw new Error(job.error?.message ?? job.message);
      }
      const document = await getProjectDocument(selectedProject.project_id, "overview");
      setOverview(document);
      setError("");
    } catch (err) {
      setError(formatError(err));
    } finally {
      setIsRefreshingOverview(false);
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        onPrimaryAction={() => setIsCreateOpen(true)}
        onSearchChange={setQuery}
        onSearchSubmit={() => void loadProjects(query)}
        primaryActionIcon="add_circle"
        primaryActionLabel="New Project"
        searchPlaceholder="Search projects, owners, or summaries..."
        searchValue={query}
        subtitle="Research workspace"
        title="Projects"
      />

      <main className="grid gap-6 p-6 sm:p-8 xl:grid-cols-[22rem_minmax(0,1fr)]">
        <aside className="rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.22em] text-on-surface-variant">
                Project Map
              </p>
              <p className="mt-1 text-xs text-on-surface-variant">
                {projects.length} projects loaded
              </p>
            </div>
            <button
              className="rounded-lg px-2 py-1 text-xs font-bold text-primary hover:bg-primary/10"
              onClick={() => void loadProjects(query)}
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
              <ProjectListSkeleton />
            ) : projects.length ? (
              projects.map((project) => (
                <button
                  className={`w-full rounded-xl px-3 py-3 text-left transition-colors ${
                    project.project_id === selectedId
                      ? "bg-primary text-on-primary"
                      : "bg-surface-container-low text-on-surface hover:bg-surface-container"
                  }`}
                  key={project.project_id}
                  ref={project.project_id === focusedProjectId ? focusedProjectRef : undefined}
                  onClick={() => setSelectedId(project.project_id)}
                  type="button"
                >
                  <span className="line-clamp-1 text-sm font-bold">
                    {project.name}
                  </span>
                  <span
                    className={`mt-1 block line-clamp-1 text-xs ${
                      project.project_id === selectedId
                        ? "text-on-primary/80"
                        : "text-on-surface-variant"
                    }`}
                  >
                    {statusLabels[project.status]} · {project.owner || "No owner"}
                  </span>
                </button>
              ))
            ) : (
              <EmptyProjectState hasQuery={Boolean(query.trim())} />
            )}
          </div>
        </aside>

        <section className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            <MetricCard label="Total" value={projects.length} />
            <MetricCard label="Researching" value={statusCounts.researching ?? 0} />
            <MetricCard
              label="Experimenting"
              value={statusCounts.experimenting ?? 0}
            />
            <MetricCard label="Writing" value={statusCounts.writing ?? 0} />
          </div>

          {selectedProject ? (
            <ProjectDetail
              isRefreshingOverview={isRefreshingOverview}
              onRefreshOverview={() => void handleRefreshOverview()}
              overview={overview}
              project={selectedProject}
            />
          ) : (
            <div className="flex min-h-[360px] flex-col items-center justify-center rounded-2xl border border-dashed border-outline-variant/40 bg-surface-container-lowest p-8 text-center">
              <span className="material-symbols-outlined text-4xl text-on-surface-variant">
                workspaces
              </span>
              <h2 className="mt-3 text-lg font-extrabold text-on-surface">
                No project selected
              </h2>
              <p className="mt-2 max-w-md text-sm text-on-surface-variant">
                Create a project to organize linked papers, knowledge, datasets, and draft modules.
              </p>
            </div>
          )}
        </section>
      </main>

      {isCreateOpen ? (
        <CreateProjectDialog
          isSubmitting={isSubmitting}
          onClose={() => setIsCreateOpen(false)}
          onSubmit={handleCreate}
        />
      ) : null}
    </div>
  );
};

function ProjectDetail({
  isRefreshingOverview,
  onRefreshOverview,
  overview,
  project,
}: {
  isRefreshingOverview: boolean;
  onRefreshOverview: () => void;
  overview: ProjectDocumentRecord | null;
  project: ProjectRecord;
}) {
  return (
    <article className="overflow-hidden rounded-2xl border border-outline-variant/10 bg-surface-container-lowest shadow-sm">
      <div className="bg-gradient-to-br from-surface-container-low via-surface-container-lowest to-secondary/10 p-6 sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-secondary">
              {statusLabels[project.status]}
            </p>
            <h2 className="mt-3 max-w-4xl text-3xl font-extrabold tracking-tight text-on-surface">
              {project.name}
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-on-surface-variant">
              {project.summary || "No summary has been recorded yet."}
            </p>
          </div>
          <button
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-bold text-on-primary shadow-sm disabled:opacity-60"
            disabled={isRefreshingOverview}
            onClick={onRefreshOverview}
            type="button"
          >
            <span className="material-symbols-outlined text-lg">
              {isRefreshingOverview ? "progress_activity" : "refresh"}
            </span>
            {isRefreshingOverview ? "Refreshing..." : "Refresh Overview"}
          </button>
        </div>
      </div>

      <div className="grid gap-6 p-6 sm:p-8 xl:grid-cols-[12rem_minmax(0,1fr)]">
        <nav className="space-y-1">
          {projectSections.map((section) => (
            <div
              className={`rounded-xl px-3 py-2 text-sm font-semibold ${
                section === "overview"
                  ? "bg-primary/10 text-primary"
                  : "text-on-surface-variant"
              }`}
              key={section}
            >
              {section.replace("_", " ")}
            </div>
          ))}
        </nav>

        <section className="rounded-2xl bg-surface-container-low p-5">
          <div className="mb-4 flex items-center justify-between gap-4">
            <h3 className="text-sm font-extrabold text-on-surface">
              Overview Document
            </h3>
            <span className="text-xs font-semibold text-on-surface-variant">
              v{overview?.version ?? "-"}
            </span>
          </div>
          <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap rounded-xl bg-surface-container-lowest p-4 text-sm leading-6 text-on-surface-variant">
            {overview?.content || "# Overview\n\nNo overview content yet."}
          </pre>
        </section>
      </div>
    </article>
  );
}

function CreateProjectDialog({
  isSubmitting,
  onClose,
  onSubmit,
}: {
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (input: ProjectCreateInput) => Promise<void>;
}) {
  const [form, setForm] = useState<ProjectCreateInput>({
    name: "",
    summary: "",
    owner: "",
    status: "planning",
  });

  function updateField(field: keyof ProjectCreateInput, value: string): void {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-on-background/35 px-4 py-8 backdrop-blur-sm">
      <div className="w-full max-w-xl rounded-2xl bg-surface-container-lowest p-6 shadow-[0_24px_80px_rgba(22,32,34,0.24)]">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-extrabold text-on-surface">
              Create Project
            </h2>
            <p className="mt-1 text-sm text-on-surface-variant">
              Create a durable workspace for papers, resources, and manuscripts.
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

        <Field
          label="Name"
          onChange={(value) => updateField("name", value)}
          placeholder="Action Prediction for AAAI 2026"
          required
          value={form.name ?? ""}
        />
        <Field
          label="Owner"
          onChange={(value) => updateField("owner", value)}
          placeholder="WMGray"
          value={form.owner ?? ""}
        />
        <label className="mt-4 block">
          <span className="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-on-surface-variant">
            Status
          </span>
          <select
            className="w-full rounded-lg border border-outline-variant/40 bg-surface-container-lowest px-3 py-3 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
            onChange={(event) => updateField("status", event.target.value)}
            value={form.status}
          >
            {Object.entries(statusLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <TextArea
          label="Summary"
          onChange={(value) => updateField("summary", value)}
          placeholder="Research question, target venue, and current hypothesis."
          value={form.summary ?? ""}
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
              {isSubmitting ? "progress_activity" : "workspaces"}
            </span>
            <span>{isSubmitting ? "Creating..." : "Create Project"}</span>
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
    <label className="mt-4 block first:mt-0">
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

function ProjectListSkeleton() {
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

function EmptyProjectState({ hasQuery }: { hasQuery: boolean }) {
  return (
    <div className="rounded-xl border border-dashed border-outline-variant/40 p-6 text-center">
      <span className="material-symbols-outlined text-3xl text-on-surface-variant">
        workspaces
      </span>
      <p className="mt-2 text-sm font-bold text-on-surface">
        {hasQuery ? "No matching projects" : "No projects yet"}
      </p>
      <p className="mt-1 text-xs text-on-surface-variant">
        {hasQuery ? "Try another query." : "Create the first project workspace."}
      </p>
    </div>
  );
}

function formatError(err: unknown): string {
  if (err instanceof APIError) {
    return `${err.code}: ${err.message}`;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Unexpected project API error.";
}
