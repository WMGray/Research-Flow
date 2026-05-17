import { Archive, BookOpen, Check, Filter, Inbox, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/app/EmptyState";
import { PageShell } from "@/components/app/PageShell";
import { BatchActionBar, type BatchAction } from "@/components/common/BatchActionBar";
import { CandidatePaperCard as CandidateCard } from "@/components/discover/CandidatePaperCard";
import { DiscoverFilters, type DiscoverFilterState } from "@/components/discover/DiscoverFilters";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useDialog } from "@/components/ui/DialogProvider";
import {
  fetchDiscoverDashboard,
  createSearchBatch,
  setCandidateBatchDecision,
  setCandidateDecision,
  type CandidateRecord,
  type CreateSearchBatchPayload,
  type DiscoverDashboardData,
} from "@/lib/api";
import { filterCandidates } from "@/lib/libraryView";

const defaultFilters: DiscoverFilterState = {
  batchId: "all",
  minScore: 0,
  maxScore: 100,
};

export function WorkflowPage() {
  const { confirm, notify } = useDialog();
  const [discoverData, setDiscoverData] = useState<DiscoverDashboardData | null>(null);
  const [filters, setFilters] = useState<DiscoverFilterState>(defaultFilters);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchDialogOpen, setSearchDialogOpen] = useState(false);
  const [busyId, setBusyId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const discoverPayload = await fetchDiscoverDashboard();
      setDiscoverData(discoverPayload.data);
      setError("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "加载发现数据失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const candidates = discoverData?.candidates ?? [];
  const batches = discoverData?.batches ?? [];
  const pendingCandidates = useMemo(() => candidates.filter((candidate) => candidate.decision === "pending"), [candidates]);
  const filtered = useMemo(() => filterCandidates(pendingCandidates, filters), [pendingCandidates, filters]);
  const activeBatch = useMemo(() => batches.find((batch) => batch.batch_id === filters.batchId) ?? null, [batches, filters.batchId]);
  const activeBatchCandidates = useMemo(
    () => (activeBatch ? pendingCandidates.filter((candidate) => candidate.batch_id === activeBatch.batch_id) : pendingCandidates),
    [activeBatch, pendingCandidates],
  );
  const selectedCandidates = useMemo(() => candidates.filter((candidate) => selectedIds.has(candidateKey(candidate))), [candidates, selectedIds]);

  const updateDecision = async (candidate: CandidateRecord, decision: "keep" | "reject") => {
    const accepted = await confirm(
      decision === "keep"
        ? {
            title: "收录这篇候选论文？",
            message: "论文会直接进入文库，保持待解析、缺 PDF 或待生成 Note 等工作流状态。",
            confirmLabel: "收录",
            cancelLabel: "取消",
          }
        : {
            title: "物理删除这篇候选论文？",
            message: "将删除候选记录和已保存的候选产物，此操作不可恢复。",
            confirmLabel: "物理删除",
            cancelLabel: "取消",
            danger: true,
          },
    );
    if (!accepted) return;

    setBusyId(candidateKey(candidate));
    try {
      await setCandidateDecision(candidate.batch_id, candidate.candidate_id, decision);
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "更新候选论文失败");
    } finally {
      setBusyId("");
    }
  };

  const batchDecision = async (decision: "keep" | "reject") => {
    const accepted = await confirm({
      title: decision === "keep" ? "批量收录候选论文？" : "批量物理删除候选论文？",
      message: decision === "keep"
        ? `将 ${selectedCandidates.length} 篇候选论文直接写入文库。`
        : `将物理删除 ${selectedCandidates.length} 篇候选论文及其已保存的候选产物，此操作不可恢复。`,
      confirmLabel: "确认",
      cancelLabel: "取消",
      danger: decision === "reject",
    });
    if (!accepted) return;

    const candidatesByBatch = new Map<string, CandidateRecord[]>();
    for (const candidate of selectedCandidates) {
      const rows = candidatesByBatch.get(candidate.batch_id) ?? [];
      rows.push(candidate);
      candidatesByBatch.set(candidate.batch_id, rows);
    }
    for (const [batchId, rows] of candidatesByBatch.entries()) {
      await setCandidateBatchDecision(batchId, rows.map((candidate) => candidate.candidate_id), decision);
    }
    setSelectedIds(new Set());
    await load();
  };

  const batchActions: BatchAction[] = [
    { id: "keep", label: "批量收录", icon: <Check className="h-3.5 w-3.5" />, onClick: () => void batchDecision("keep") },
    { id: "delete", label: "批量物理删除", icon: <Trash2 className="h-3.5 w-3.5" />, variant: "destructive", onClick: () => void batchDecision("reject") },
  ];

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] min-w-0">
      <PageShell
        actions={
          <Button size="sm" variant="outline" onClick={() => setSearchDialogOpen(true)}>
            <Filter className="h-4 w-4" />
            新建检索
          </Button>
        }
        className="min-w-0 flex-1"
        description="以卡片流筛选候选论文，支持批量收录、剔除和多维筛选。"
        title="发现"
      >
        {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <SummaryTile icon={Search} label="检索批次" value={discoverData?.summary.batch_total ?? 0} />
          <SummaryTile icon={Inbox} label={activeBatch ? "当前 Batch 候选" : "候选论文"} value={activeBatchCandidates.length} />
          <SummaryTile icon={Check} label={activeBatch ? "当前 Batch 已收录" : "已收录"} value={activeBatch?.keep_total ?? discoverData?.summary.keep_total ?? 0} />
          <SummaryTile icon={BookOpen} label={activeBatch ? "当前 Batch 已剔除" : "已剔除"} value={activeBatch?.reject_total ?? discoverData?.summary.reject_total ?? 0} />
        </section>

        <DiscoverFilters
          batches={batches}
          filters={filters}
          onChange={setFilters}
          onClear={() => setFilters(defaultFilters)}
        />

        <BatchActionBar actions={batchActions} count={selectedIds.size} onClear={() => setSelectedIds(new Set())} />

        {filtered.length > 0 ? (
          <section className="grid gap-3 lg:grid-cols-2 2xl:grid-cols-3">
            {filtered.map((candidate) => (
              <CandidateCard
                batchMode={selectedIds.size > 0}
                busy={busyId === candidateKey(candidate)}
                candidate={candidate}
                checked={selectedIds.has(candidateKey(candidate))}
                key={`${candidate.batch_id}-${candidate.candidate_id}`}
                selected={false}
                onDecision={updateDecision}
                onSelect={() => undefined}
                onToggle={() =>
                  setSelectedIds((current) => {
                    const next = new Set(current);
                    const key = candidateKey(candidate);
                    if (next.has(key)) next.delete(key);
                    else next.add(key);
                    return next;
                  })
                }
              />
            ))}
          </section>
        ) : (
          <EmptyState
            description={loading ? "正在读取发现数据。" : "当前筛选条件下没有待处理候选论文。"}
            icon={Archive}
            title={loading ? "加载中" : "没有候选论文"}
          />
        )}
      </PageShell>
      <NewSearchDialog
        open={searchDialogOpen}
        onOpenChange={setSearchDialogOpen}
        onSubmit={async (payload) => {
          try {
            const response = await createSearchBatch(payload);
            setSearchDialogOpen(false);
            setFilters((current) => ({ ...current, batchId: response.data.batch.batch_id }));
            await load();
            notify({
              title: "检索 Batch 已创建",
              message: response.data.batch.batch_id,
            });
          } catch (err: unknown) {
            notify({
              title: "创建检索失败",
              message: err instanceof Error ? err.message : "请检查关键词和 Settings prompt。",
            });
          }
        }}
      />
    </div>
  );
}

function SummaryTile({ icon: Icon, label, value }: { icon: typeof Search; label: string; value: number }) {
  return (
    <Card className="flex items-center justify-between gap-3 p-3">
      <div>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="mt-1 text-xl font-semibold">{value}</div>
      </div>
      <div className="grid h-8 w-8 place-items-center rounded-md bg-muted text-muted-foreground">
        <Icon className="h-4 w-4" />
      </div>
    </Card>
  );
}

function NewSearchDialog({
  onOpenChange,
  onSubmit,
  open,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: CreateSearchBatchPayload) => Promise<void>;
}) {
  const [keywords, setKeywords] = useState("");
  const [venue, setVenue] = useState("");
  const [yearStart, setYearStart] = useState("");
  const [yearEnd, setYearEnd] = useState("");
  const [source, setSource] = useState("arxiv");
  const [maxResults, setMaxResults] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    const cleanKeywords = keywords.trim();
    if (!cleanKeywords) return;
    setSubmitting(true);
    try {
      await onSubmit({
        keywords: cleanKeywords,
        venue: venue.trim(),
        year_start: yearStart ? Number(yearStart) : null,
        year_end: yearEnd ? Number(yearEnd) : null,
        source,
        max_results: maxResults ? Number(maxResults) : null,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>新建检索</DialogTitle>
          <DialogDescription>提交关键词后，后端会读取 Settings 中的 prompt template，并写出 search batch/job/candidates。</DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          <Input autoFocus placeholder="关键词，例如 representation learning" value={keywords} onChange={(event) => setKeywords(event.target.value)} />
          <Input placeholder="Venue，例如 NeurIPS, ICML, ICLR" value={venue} onChange={(event) => setVenue(event.target.value)} />
          <div className="grid grid-cols-2 gap-2">
            <Input placeholder="起始年份" type="number" value={yearStart} onChange={(event) => setYearStart(event.target.value)} />
            <Input placeholder="结束年份" type="number" value={yearEnd} onChange={(event) => setYearEnd(event.target.value)} />
          </div>
          <Select value={source} onValueChange={setSource}>
            <SelectTrigger>
              <SelectValue placeholder="来源" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="arxiv">arXiv</SelectItem>
              <SelectItem value="semantic-scholar">Semantic Scholar</SelectItem>
              <SelectItem value="local">Local</SelectItem>
            </SelectContent>
          </Select>
          <Input placeholder="最大数量" type="number" value={maxResults} onChange={(event) => setMaxResults(event.target.value)} />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button disabled={!keywords.trim() || submitting} onClick={() => void submit()}>
            {submitting ? "创建中" : "创建检索"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function candidateKey(candidate: CandidateRecord): string {
  return `${candidate.batch_id}:${candidate.candidate_id}`;
}
