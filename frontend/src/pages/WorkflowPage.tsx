import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { type AppIconName } from "@/components/ui/AppIcon";
import { useDialog } from "@/components/ui/DialogProvider";
import { AcquireWorkflowView, type IngestForm, SearchWorkflowView } from "@/components/workflow/WorkflowPanels";
import { WorkflowHero, WorkflowMetricCard, WorkflowTabs, type WorkflowView } from "@/components/workflow/WorkflowChrome";
import {
  fetchAcquireDashboard,
  fetchDiscoverDashboard,
  ingestPaper,
  markPaperReview,
  migratePaper,
  parsePaperPdf,
  rejectPaper,
  setCandidateDecision,
  type AcquireDashboardData,
  type CandidateRecord,
  type DiscoverDashboardData,
  type IngestPaperPayload,
  type PaperRecord,
} from "@/lib/api";

const emptyIngestForm: IngestForm = {
  source: "",
  domain: "",
  area: "",
  topic: "",
  target_path: "",
  move: false,
};

export function WorkflowPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { confirm } = useDialog();
  const [discoverData, setDiscoverData] = useState<DiscoverDashboardData | null>(null);
  const [acquireData, setAcquireData] = useState<AcquireDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [candidateBusyId, setCandidateBusyId] = useState("");
  const [paperBusyId, setPaperBusyId] = useState("");
  const [transferBusy, setTransferBusy] = useState("");
  const [candidateQuery, setCandidateQuery] = useState("");
  const [candidateSourceFilter, setCandidateSourceFilter] = useState("all");
  const [selectedBatchId, setSelectedBatchId] = useState("all");
  const [acquireQuery, setAcquireQuery] = useState("");
  const [acquireStatus, setAcquireStatus] = useState("all");
  const [form, setForm] = useState<IngestForm>(emptyIngestForm);
  const [sourceOptions, setSourceOptions] = useState<string[]>([]);

  const view: WorkflowView = searchParams.get("view") === "acquire" ? "acquire" : "search";

  const load = () => {
    setLoading(true);
    void Promise.all([fetchDiscoverDashboard(), fetchAcquireDashboard()])
      .then(([discoverPayload, acquirePayload]) => {
        setDiscoverData(discoverPayload.data);
        setAcquireData(acquirePayload.data);
        setSourceOptions(
          Array.from(new Set(discoverPayload.data.candidates.map((candidate) => candidate.source_type || "local"))).sort(),
        );
        setError("");
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "加载 Workflow 数据失败"))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const metrics = useMemo(() => {
    const discoverSummary = discoverData?.summary ?? {};
    const acquireSummary = acquireData?.summary ?? {};
    const batches = discoverData?.batches ?? [];
    const candidates = discoverData?.candidates ?? [];
    const queue = acquireData?.queue ?? [];

    return [
      { icon: "search", label: "检索批次", value: discoverSummary.batch_total ?? 0, note: `当前有 ${batches.length} 个待处理批次` },
      { icon: "document", label: "待查看候选", value: discoverSummary.candidate_total ?? 0, note: `当前共有 ${candidates.length} 篇待筛选论文` },
      { icon: "list", label: "Acquire 队列", value: acquireSummary.curated_total ?? 0, note: `当前已推进 ${queue.length} 篇论文` },
      { icon: "download", label: "缺少 PDF", value: acquireSummary.needs_pdf_total ?? 0, note: "需要补齐源 PDF" },
      { icon: "clock", label: "待审核", value: acquireSummary.needs_review_total ?? 0, note: "等待人工确认" },
      { icon: "folder", label: "解析失败", value: acquireSummary.parse_failed_total ?? 0, note: "需要继续排查处理" },
    ] as const satisfies ReadonlyArray<{
      icon: AppIconName;
      label: string;
      value: number;
      note: string;
    }>;
  }, [acquireData, discoverData]);

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
            title: "确认保留该论文？",
            message: "该操作会将论文从当前待处理列表移除，并推进到 Acquire 阶段继续处理。",
            confirmLabel: "确认保留",
            cancelLabel: "取消",
            danger: false,
          }
        : {
            title: "确认删除该候选论文？",
            message: "该操作会移除候选条目，并删除关联落地文件或文件夹。此操作不可恢复。",
            confirmLabel: "确认删除",
            cancelLabel: "取消",
            danger: true,
          },
    );
    if (!accepted) {
      return;
    }

    setCandidateBusyId(candidate.candidate_id);
    void setCandidateDecision(candidate.batch_id, candidate.candidate_id, decision)
      .then(load)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "更新候选决策失败"))
      .finally(() => setCandidateBusyId(""));
  };

  const runPaperAction = async (paper: PaperRecord, action: "parse" | "review" | "reject") => {
    if (action === "reject") {
      const accepted = await confirm({
        title: "确认删除该论文？",
        message: "该操作会删除论文目录及其所有文件，并从当前 Acquire 队列中移除。此操作不可恢复。",
        confirmLabel: "确认删除",
        cancelLabel: "取消",
        danger: true,
      });
      if (!accepted) {
        return;
      }
    }

    setPaperBusyId(paper.paper_id);
    const request =
      action === "parse"
        ? parsePaperPdf(paper.paper_id, false)
        : action === "review"
          ? markPaperReview(paper.paper_id)
          : rejectPaper(paper.paper_id);

    void request
      .then(load)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "执行论文操作失败"))
      .finally(() => setPaperBusyId(""));
  };

  const updateForm = (field: keyof IngestForm, value: string | boolean) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const transferPaper = (mode: "ingest" | "migrate") => {
    const source = form.source.trim();
    if (!source) {
      setError("请先填写源路径。");
      return;
    }

    const payload: IngestPaperPayload = {
      source,
      domain: form.domain.trim() || undefined,
      area: form.area.trim() || undefined,
      topic: form.topic.trim() || undefined,
      target_path: form.target_path.trim() || undefined,
      move: mode === "migrate" ? true : form.move,
    };

    setTransferBusy(mode);
    const request = mode === "migrate" ? migratePaper(payload) : ingestPaper(payload);

    void request
      .then(() => {
        setForm(emptyIngestForm);
        load();
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "执行入库或迁移失败"))
      .finally(() => setTransferBusy(""));
  };

  return (
    <>
      <TopBar current="Workflow" section="研究工作台 > 论文流程" title="Workflow" />
      <main className="page workflow-page workflow-shell">
        <WorkflowTabs currentView={view} onChange={setView} />
        <WorkflowHero view={view} />
        {error ? <div className="error-banner">{error}</div> : null}
        <section className="metric-strip workflow-metric-strip">
          {metrics.map((metric) => (
            <WorkflowMetricCard key={metric.label} {...metric} />
          ))}
        </section>

        {view === "search" ? (
          <SearchWorkflowView
            batches={discoverData?.batches ?? []}
            candidateBusyId={candidateBusyId}
            candidateQuery={candidateQuery}
            candidateSourceFilter={candidateSourceFilter}
            candidates={discoverData?.candidates ?? []}
            loading={loading}
            onCandidateDecision={updateDecision}
            onCandidateQueryChange={setCandidateQuery}
            onCandidateSourceFilterChange={setCandidateSourceFilter}
            onSelectedBatchChange={setSelectedBatchId}
            selectedBatchId={selectedBatchId}
            sourceOptions={sourceOptions}
          />
        ) : (
          <AcquireWorkflowView
            acquireQuery={acquireQuery}
            acquireStatus={acquireStatus}
            acquireSummary={acquireData?.summary ?? {}}
            form={form}
            loading={loading}
            onAcquireQueryChange={setAcquireQuery}
            onAcquireStatusChange={setAcquireStatus}
            onFormChange={updateForm}
            onPaperAction={runPaperAction}
            onTransfer={transferPaper}
            paperBusyId={paperBusyId}
            queue={acquireData?.queue ?? []}
            transferBusy={transferBusy}
          />
        )}
      </main>
    </>
  );
}
