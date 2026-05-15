import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { TopBar } from "@/components/layout/TopBar";
import { type AppIconName } from "@/components/ui/AppIcon";
import { useDialog } from "@/components/ui/DialogProvider";
import {
  AcquireWorkflowView,
  SearchWorkflowView,
  type AcquireStageView,
  type CandidateScoreSort,
  type CandidateYearSort,
  type PaperAction,
  type PaperActionMap,
} from "@/components/workflow/WorkflowPanels";
import { WorkflowHero, WorkflowMetricCard, WorkflowTabs, type WorkflowView } from "@/components/workflow/WorkflowChrome";
import {
  acceptPaper,
  fetchAcquireDashboard,
  fetchDiscoverDashboard,
  generatePaperNote,
  parsePaperPdf,
  rejectPaper,
  setCandidateDecision,
  type AcquireDashboardData,
  type CandidateRecord,
  type DiscoverDashboardData,
  type PaperRecord,
} from "@/lib/api";

export function WorkflowPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { confirm } = useDialog();
  const [discoverData, setDiscoverData] = useState<DiscoverDashboardData | null>(null);
  const [acquireData, setAcquireData] = useState<AcquireDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [candidateBusyId, setCandidateBusyId] = useState("");
  const [paperActionMap, setPaperActionMap] = useState<PaperActionMap>({});
  const [candidateQuery, setCandidateQuery] = useState("");
  const [candidateSourceFilter, setCandidateSourceFilter] = useState("all");
  const [candidateYearSort, setCandidateYearSort] = useState<CandidateYearSort>("none");
  const [candidateScoreSort, setCandidateScoreSort] = useState<CandidateScoreSort>("desc");
  const [selectedBatchId, setSelectedBatchId] = useState("all");
  const [acquireQuery, setAcquireQuery] = useState("");
  const [acquireStageView, setAcquireStageView] = useState<AcquireStageView>("acquire");

  const view: WorkflowView = searchParams.get("view") === "acquire" ? "acquire" : "search";
  const isAcquireView = view === "acquire";

  const load = async () => {
    setLoading(true);
    try {
      const [discoverPayload, acquirePayload] = await Promise.all([fetchDiscoverDashboard(), fetchAcquireDashboard()]);
      setDiscoverData(discoverPayload.data);
      setAcquireData(acquirePayload.data);
      setError("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load workflow data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (!discoverData) {
      return;
    }
    if (selectedBatchId !== "all" && !discoverData.batches.some((batch) => batch.batch_id === selectedBatchId)) {
      setSelectedBatchId("all");
    }
  }, [discoverData, selectedBatchId]);

  const sourceOptions = useMemo(() => {
    const rawOptions = discoverData?.candidates.map((candidate) => candidate.source_type || "Local") ?? [];
    return Array.from(new Set(rawOptions)).sort();
  }, [discoverData]);

  const metrics = useMemo(() => {
    const discoverSummary = discoverData?.summary ?? {};
    const acquireSummary = acquireData?.summary ?? {};
    const queue = acquireData?.queue ?? [];
    const parsedTotal = queue.filter((paper) => paper.parser_status === "parsed").length;

    if (isAcquireView) {
      return [
        { icon: "list", label: "Curated Queue", value: acquireSummary.curated_total ?? 0, note: "Curated papers in pipeline" },
        { icon: "download", label: "Needs PDF", value: acquireSummary.needs_pdf_total ?? 0, note: "PDF not ready" },
        { icon: "spark", label: "Parsed", value: parsedTotal, note: "Structured outputs available" },
        { icon: "clock", label: "Needs Review", value: acquireSummary.needs_review_total ?? 0, note: "Waiting for Gate 2" },
      ] as const satisfies ReadonlyArray<{
        icon: AppIconName;
        label: string;
        value: number;
        note: string;
      }>;
    }

    return [
      { icon: "search", label: "Search Batches", value: discoverSummary.batch_total ?? 0, note: "Active search batches" },
      { icon: "document", label: "Candidates", value: discoverSummary.candidate_total ?? 0, note: "Pending candidate review" },
      { icon: "check", label: "Gate 1 Keep", value: discoverSummary.keep_total ?? 0, note: "Promoted into acquire" },
      { icon: "list", label: "Acquire Queue", value: acquireSummary.curated_total ?? 0, note: "Papers already in acquire" },
    ] as const satisfies ReadonlyArray<{
      icon: AppIconName;
      label: string;
      value: number;
      note: string;
    }>;
  }, [acquireData, discoverData, isAcquireView]);

  const setView = (nextView: WorkflowView) => {
    const nextParams = new URLSearchParams(searchParams);
    if (nextView === "search") {
      nextParams.delete("view");
    } else {
      nextParams.set("view", nextView);
    }
    setSearchParams(nextParams);
  };

  const updateDecision = async (candidate: CandidateRecord, decision: "keep" | "reject") => {
    const accepted = await confirm(
      decision === "keep"
        ? {
            title: "Keep this candidate?",
            message: "This moves the paper into the acquire queue.",
            confirmLabel: "Keep",
            cancelLabel: "Cancel",
            danger: false,
          }
        : {
            title: "Reject this candidate?",
            message: "This removes the candidate entry and its downloaded artifacts.",
            confirmLabel: "Reject",
            cancelLabel: "Cancel",
            danger: true,
          },
    );
    if (!accepted) {
      return;
    }

    setCandidateBusyId(candidate.candidate_id);
    try {
      await setCandidateDecision(candidate.batch_id, candidate.candidate_id, decision);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update candidate decision.");
    } finally {
      setCandidateBusyId("");
    }
  };

  const runPaperAction = async (paper: PaperRecord, action: PaperAction) => {
    if (action === "reject") {
      const accepted = await confirm({
        title: "Delete this paper?",
        message: "This removes the paper directory and all files from the acquire queue.",
        confirmLabel: "Delete",
        cancelLabel: "Cancel",
        danger: true,
      });
      if (!accepted) {
        return;
      }
    }

    setPaperActionMap((current) => ({ ...current, [paper.paper_id]: action }));
    try {
      if (action === "parse") {
        await parsePaperPdf(paper.paper_id, paper.parser_status === "failed");
      } else if (action === "accept") {
        await acceptPaper(paper.paper_id);
      } else if (action === "note") {
        await generatePaperNote(paper.paper_id, false);
      } else {
        await rejectPaper(paper.paper_id);
      }
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to run paper action.");
    } finally {
      setPaperActionMap((current) => {
        const next = { ...current };
        delete next[paper.paper_id];
        return next;
      });
    }
  };

  return (
    <>
      <TopBar current="Workflow" section="Research Workspace > Workflow" title="Workflow" />
      <main className={`page workflow-page workflow-shell ${isAcquireView ? "workflow-page-acquire" : "workflow-page-search"}`}>
        <div className="workflow-page-header">
          <section className={`workflow-page-heading ${isAcquireView ? "compact" : ""}`}>
            <h1>Workflow Dashboard</h1>
            <p>{isAcquireView ? "Operate the acquire queue directly from the main workbench." : "Search overview and workflow management."}</p>
          </section>

          <WorkflowTabs currentView={view} onChange={setView} />
        </div>

        {!isAcquireView ? <WorkflowHero view={view} /> : null}
        {error ? <div className="error-banner">{error}</div> : null}

        <section className={`metric-strip workflow-metric-strip ${isAcquireView ? "workflow-metric-strip-acquire" : ""}`}>
          {metrics.map((metric) => (
            <WorkflowMetricCard key={metric.label} {...metric} />
          ))}
        </section>

        {isAcquireView ? (
          <AcquireWorkflowView
            acquireQuery={acquireQuery}
            currentStageView={acquireStageView}
            loading={loading}
            onAcquireQueryChange={setAcquireQuery}
            onAcquireStageChange={setAcquireStageView}
            onPaperAction={runPaperAction}
            onSwitchToSearch={() => setView("search")}
            paperActionMap={paperActionMap}
            queue={acquireData?.queue ?? []}
          />
        ) : (
          <SearchWorkflowView
            batches={discoverData?.batches ?? []}
            candidateBusyId={candidateBusyId}
            candidateQuery={candidateQuery}
            candidateScoreSort={candidateScoreSort}
            candidateSourceFilter={candidateSourceFilter}
            candidateYearSort={candidateYearSort}
            candidates={discoverData?.candidates ?? []}
            loading={loading}
            onCandidateDecision={updateDecision}
            onCandidateQueryChange={setCandidateQuery}
            onCandidateScoreSortChange={setCandidateScoreSort}
            onCandidateSourceFilterChange={setCandidateSourceFilter}
            onCandidateYearSortChange={setCandidateYearSort}
            onSelectedBatchChange={setSelectedBatchId}
            selectedBatchId={selectedBatchId}
            sourceOptions={sourceOptions}
          />
        )}
      </main>
    </>
  );
}
