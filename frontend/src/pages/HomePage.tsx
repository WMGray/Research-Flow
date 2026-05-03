import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  EmptyState,
  MetricCard,
  MiniList,
  Panel,
  ProgressRow,
  StatusPill,
} from "@/components/dashboard/DashboardWidgets";
import { TopBar } from "@/components/layout/TopBar";
import {
  type DatasetRecord,
  type JobRecord,
  type KnowledgeRecord,
  type LLMStatusRecord,
  type PaperRecord,
  type ProjectRecord,
  listDatasets,
  listJobs,
  listKnowledge,
  listLLMStatus,
  listPapers,
  listProjects,
} from "@/lib/api";

type DashboardState = {
  papers: PaperRecord[];
  paperTotal: number;
  datasets: DatasetRecord[];
  datasetTotal: number;
  knowledge: KnowledgeRecord[];
  knowledgeTotal: number;
  projects: ProjectRecord[];
  projectTotal: number;
  jobs: JobRecord[];
  llms: LLMStatusRecord[];
};

const initialState: DashboardState = {
  papers: [],
  paperTotal: 0,
  datasets: [],
  datasetTotal: 0,
  knowledge: [],
  knowledgeTotal: 0,
  projects: [],
  projectTotal: 0,
  jobs: [],
  llms: [],
};

const finalJobStatuses = new Set(["succeeded", "failed", "cancelled"]);

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatPercent(value: number, total: number): string {
  if (total <= 0) {
    return "0%";
  }
  return `${Math.round((value / total) * 100)}%`;
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

export const HomePage: React.FC = () => {
  const [state, setState] = useState<DashboardState>(initialState);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadDashboard(): Promise<void> {
      setLoading(true);
      setError("");
      try {
        const [paperPage, datasetPage, knowledgePage, projectPage, jobPage, llms] =
          await Promise.all([
            listPapers({ pageSize: 6, sort: "updated_at", order: "desc" }, controller.signal),
            listDatasets({ pageSize: 5 }),
            listKnowledge({ pageSize: 6 }),
            listProjects({ pageSize: 5 }),
            listJobs({ pageSize: 6 }),
            listLLMStatus(),
          ]);

        setState({
          papers: paperPage.papers,
          paperTotal: paperPage.total,
          datasets: datasetPage.datasets,
          datasetTotal: datasetPage.total,
          knowledge: knowledgePage.knowledge,
          knowledgeTotal: knowledgePage.total,
          projects: projectPage.projects,
          projectTotal: projectPage.total,
          jobs: jobPage.jobs,
          llms,
        });
      } catch (exc) {
        if (!controller.signal.aborted) {
          setError(exc instanceof Error ? exc.message : "Failed to load dashboard.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadDashboard();
    return () => controller.abort();
  }, []);

  const realPdfCount = state.papers.filter((paper) => paper.source_pdf_is_real).length;
  const refinedCount = state.papers.filter(
    (paper) => paper.refine_status === "succeeded" || paper.paper_stage === "refined",
  ).length;
  const reviewReadyCount = state.papers.filter(
    (paper) => paper.review_status === "waiting_review",
  ).length;
  const runningJobs = state.jobs.filter((job) => !finalJobStatuses.has(job.status)).length;
  const healthyLlms = state.llms.filter(
    (llm) => llm.connectivity_status === "ok" || llm.connectivity_status === "available",
  ).length;
  const acceptedKnowledgeCount = state.knowledge.filter(
    (item) => item.review_status === "accepted",
  ).length;
  const pendingKnowledgeCount = state.knowledge.filter(
    (item) => item.review_status === "pending_review",
  ).length;

  return (
    <div className="flex min-h-full flex-col">
      <TopBar />
      <main className="flex-1 p-6 sm:p-8">
        <div className="mx-auto max-w-[1600px] space-y-8 pb-12">
          <header className="flex flex-col justify-between gap-4 rounded-[2rem] border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm lg:flex-row lg:items-end">
            <div>
              <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-primary">
                Research-Flow Live Dashboard
              </p>
              <h1 className="text-3xl font-black tracking-tight text-on-background">
                Workspace health and review queue
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-on-surface-variant">
                Counts and activity below come from the backend APIs. Empty sections mean
                there is no stored data yet, not hidden mock content.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                className="rounded-xl bg-primary px-4 py-2 text-xs font-bold text-on-primary shadow-sm transition hover:bg-primary-dim"
                to="/library"
              >
                Import Paper
              </Link>
              <Link
                className="rounded-xl bg-surface-container-high px-4 py-2 text-xs font-bold text-on-surface transition hover:bg-surface-container-highest"
                to="/projects"
              >
                Open Projects
              </Link>
            </div>
          </header>

          {error ? (
            <div className="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm font-medium text-error">
              {error}
            </div>
          ) : null}

          <section className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              icon="library_books"
              label="Total papers"
              loading={loading}
              primary={formatNumber(state.paperTotal)}
              secondary={`${realPdfCount}/${state.papers.length} latest items have verified PDFs`}
            >
              <ProgressRow
                label="Refined"
                tone="primary"
                value={refinedCount}
                width={formatPercent(refinedCount, state.papers.length)}
              />
              <ProgressRow
                label="Waiting review"
                tone="amber"
                value={reviewReadyCount}
                width={formatPercent(reviewReadyCount, state.papers.length)}
              />
            </MetricCard>

            <MetricCard
              icon="database"
              label="Datasets"
              loading={loading}
              primary={formatNumber(state.datasetTotal)}
              secondary="Grounded dataset assets in backend/data"
            >
              <MiniList
                emptyLabel="No dataset has been extracted or created yet."
                items={state.datasets.map((dataset) => ({
                  key: String(dataset.dataset_id),
                  title: dataset.name,
                  detail: dataset.task_type || dataset.data_domain || "Dataset",
                }))}
              />
            </MetricCard>

            <MetricCard
              icon="psychology"
              label="Knowledge views"
              loading={loading}
              primary={formatNumber(state.knowledgeTotal)}
              secondary="Evidence-grounded insights extracted from papers"
            >
              <ProgressRow
                label="Accepted"
                tone="primary"
                value={acceptedKnowledgeCount}
                width={formatPercent(acceptedKnowledgeCount, state.knowledge.length)}
              />
              <ProgressRow
                label="Pending"
                tone="gray"
                value={pendingKnowledgeCount}
                width={formatPercent(pendingKnowledgeCount, state.knowledge.length)}
              />
            </MetricCard>

            <MetricCard
              icon="task_alt"
              label="Active jobs"
              loading={loading}
              primary={formatNumber(runningJobs)}
              secondary={`${state.jobs.length} recent job records loaded`}
            >
              <MiniList
                emptyLabel="No job records yet."
                items={state.jobs.slice(0, 3).map((job) => ({
                  key: job.job_id,
                  title: job.type,
                  detail: `${job.status} - ${job.progress}%`,
                }))}
              />
            </MetricCard>
          </section>

          <section className="grid grid-cols-10 gap-6">
            <div className="col-span-10 rounded-[2rem] border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm lg:col-span-7">
              <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
                <div>
                  <h2 className="text-2xl font-black tracking-tight text-on-background">
                    Recent papers
                  </h2>
                  <p className="text-sm text-on-surface-variant">
                    Latest imported or updated papers, including review and PDF integrity state.
                  </p>
                </div>
                <Link className="text-sm font-bold text-primary hover:underline" to="/library">
                  View library
                </Link>
              </div>

              <div className="space-y-3">
                {state.papers.length === 0 && !loading ? (
                  <EmptyState label="No papers found. Import one from Library to start the pipeline." />
                ) : null}
                {state.papers.map((paper) => (
                  <article
                    className="rounded-2xl border border-outline-variant/10 bg-surface-container-low/40 p-4 transition hover:border-primary/20"
                    key={paper.paper_id}
                  >
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                      <div className="min-w-0">
                        <h3 className="truncate text-sm font-extrabold text-on-surface">
                          {paper.title}
                        </h3>
                        <p className="mt-1 text-xs text-on-surface-variant">
                          {[paper.venue_short || paper.venue, paper.year].filter(Boolean).join(" - ") ||
                            "Metadata pending"}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <StatusPill label={paper.paper_stage || "created"} />
                        <StatusPill
                          label={paper.source_pdf_is_real ? "real PDF" : "PDF pending"}
                          tone={paper.source_pdf_is_real ? "success" : "muted"}
                        />
                        <StatusPill
                          label={paper.review_status || "not reviewed"}
                          tone={paper.review_status === "waiting_review" ? "warning" : "muted"}
                        />
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <aside className="col-span-10 space-y-6 lg:col-span-3">
              <Panel title="Projects" icon="account_tree">
                <MiniList
                  emptyLabel="No project records yet."
                  items={state.projects.map((project) => ({
                    key: String(project.project_id),
                    title: project.name,
                    detail: `${project.status} - ${formatDate(project.updated_at)}`,
                  }))}
                />
                <div className="mt-4 text-xs font-semibold text-on-surface-variant">
                  Total projects: {formatNumber(state.projectTotal)}
                </div>
              </Panel>

              <Panel title="LLM Connectivity" icon="router">
                <div className="mb-4 rounded-2xl bg-primary/5 px-4 py-3">
                  <span className="text-2xl font-black text-primary">
                    {healthyLlms}/{state.llms.length}
                  </span>
                  <span className="ml-2 text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                    available
                  </span>
                </div>
                <MiniList
                  emptyLabel="No LLM profile status loaded."
                  items={state.llms.slice(0, 5).map((llm) => ({
                    key: llm.profile_key,
                    title: llm.profile_key,
                    detail: `${llm.provider}/${llm.model_name} - ${llm.connectivity_status}`,
                  }))}
                />
              </Panel>
            </aside>
          </section>
        </div>
      </main>
    </div>
  );
};
