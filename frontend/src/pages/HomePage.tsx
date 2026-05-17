import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock,
  FileText,
  Inbox,
  Layers,
  RefreshCw,
  Search,
  Sparkles,
  Tags,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/app/EmptyState";
import { PageShell } from "@/components/app/PageShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  fetchHomeDashboard,
  generatePaperNote,
  parsePaperPdf,
  type APIEnvelope,
  type HomeDashboardData,
  type PaperRecord,
} from "@/lib/api";
import { compactNumber, formatDate, paperSummary } from "@/lib/format";
import { derivePaperStatus, domainDistribution, groupQueueByWorkflow, libraryOverviewStats } from "@/lib/libraryView";

export function HomePage() {
  const [payload, setPayload] = useState<APIEnvelope<HomeDashboardData> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      setPayload(await fetchHomeDashboard());
      setError("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "加载概览失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const totals = payload?.data.totals ?? {};
  const recentPapers = payload?.data.recent_papers ?? [];
  const queueItems = payload?.data.queue_items ?? [];
  const allKnown = useMemo(() => mergePapers(queueItems, recentPapers), [queueItems, recentPapers]);
  const stats = useMemo(() => libraryOverviewStats(allKnown), [allKnown]);
  const queueGroups = useMemo(() => groupQueueByWorkflow(allKnown), [allKnown]);
  const distribution = useMemo(() => domainDistribution(allKnown).slice(0, 6), [allKnown]);
  const failureItems = allKnown.filter((paper) => paper.parser_status === "failed" || Boolean(paper.error)).slice(0, 5);
  const readProgress = useMemo(() => {
    const total = totals.papers ?? stats.total;
    const read = totals.processed ?? stats.notes;
    return total > 0 ? Math.round((read / total) * 100) : 0;
  }, [stats.notes, stats.total, totals]);

  const runQuickAction = async (paper: PaperRecord, action: "parse" | "note") => {
    setBusyId(`${action}:${paper.paper_id}`);
    try {
      if (action === "parse") {
        await parsePaperPdf(paper.paper_id, paper.parser_status === "failed");
      } else {
        await generatePaperNote(paper.paper_id, false);
      }
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "执行快速操作失败");
    } finally {
      setBusyId("");
    }
  };

  const overviewMetrics = [
    { key: "papers", label: "论文总量", icon: FileText, value: totals.papers ?? stats.total },
    { key: "batches", label: "检索批次", icon: Search, value: totals.batches ?? 0 },
    { key: "curated", label: "待处理", icon: Inbox, value: totals.curated ?? queueItems.length },
    { key: "library", label: "已入库", icon: BookOpen, value: totals.library ?? 0 },
    { key: "needs_review", label: "待审阅", icon: Clock, value: totals.needs_review ?? 0 },
    { key: "parse_failed", label: "解析失败", icon: AlertCircle, value: totals.parse_failed ?? stats.parseFailed },
    { key: "unclassified", label: "未分类", icon: Tags, value: stats.unclassified, to: "/uncategorized" },
    { key: "missing_pdf", label: "缺少 PDF", icon: FileText, value: stats.missingPdf },
    { key: "recent_parsed", label: "最近解析成功", icon: CheckCircle2, value: stats.recentParseSuccess },
    { key: "this_week", label: "本周新增", icon: Layers, value: stats.thisWeek },
  ];

  return (
    <PageShell
      actions={
        <>
          <Button asChild size="sm" variant="outline">
            <Link to="/discover">发现论文</Link>
          </Button>
          <Button asChild size="sm">
            <Link to="/library">打开文库</Link>
          </Button>
        </>
      }
      description="统计、最近导入、待处理、阅读进度和失败任务集中展示，复杂编辑留到文库和详情页。"
      title="概览"
    >
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {overviewMetrics.map((metric) => {
          const Icon = metric.icon;
          const content = (
            <Card className="p-3 transition-colors hover:border-neutral-400">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-xs text-muted-foreground">{metric.label}</div>
                  <div className="mt-1 text-2xl font-semibold">{loading ? "..." : compactNumber(metric.value)}</div>
                </div>
                <div className="grid h-8 w-8 place-items-center rounded-md bg-muted text-muted-foreground">
                  <Icon className="h-4 w-4" />
                </div>
              </div>
            </Card>
          );
          return metric.to ? (
            <Link key={metric.key} to={metric.to}>
              {content}
            </Link>
          ) : (
            <div key={metric.key}>{content}</div>
          );
        })}
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        <Card>
          <CardHeader className="flex-row items-center justify-between gap-3 space-y-0 pb-3">
            <CardTitle className="text-base">最近导入</CardTitle>
            <Button asChild size="sm" variant="ghost">
              <Link to="/library">
                查看全部
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="grid gap-1">
            {recentPapers.length > 0 ? (
              recentPapers.slice(0, 6).map((paper) => <PaperRow busyId={busyId} key={paper.paper_id} paper={paper} onQuickAction={runQuickAction} />)
            ) : (
              <EmptyState className="min-h-36 border-0 bg-muted/40" description="从发现页收录论文后，这里会显示最近更新。" icon={BookOpen} title="暂无导入记录" />
            )}
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <ProgressCard readProgress={readProgress} stats={stats} totals={totals} />
          <WorkflowFunnel stats={stats} totals={totals} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">待处理论文</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {queueGroups.map((group) => (
              <div className="rounded-md border bg-background/60 p-2" key={group.label}>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="text-sm font-medium">{group.label}</div>
                  <StatusBadge status={group.status} />
                </div>
                {group.items.slice(0, 2).map((paper) => (
                  <CompactPaperRow key={`${group.label}-${paper.paper_id}`} paper={paper} />
                ))}
                {group.items.length === 0 ? <div className="text-xs text-muted-foreground">暂无</div> : null}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">领域分布</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {distribution.map(([domain, count]) => (
              <div className="grid grid-cols-[minmax(0,1fr)_48px] items-center gap-3" key={domain}>
                <div className="min-w-0">
                  <div className="truncate text-sm">{domain}</div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-neutral-600" style={{ width: `${stats.total > 0 ? Math.round((count / stats.total) * 100) : 0}%` }} />
                  </div>
                </div>
                <div className="text-right text-sm font-medium">{count}</div>
              </div>
            ))}
            {distribution.length === 0 ? <div className="text-sm text-muted-foreground">暂无领域统计。</div> : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">最近失败任务</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {failureItems.length > 0 ? (
              failureItems.map((paper) => (
                <div className="rounded-md border bg-red-50/60 p-2" key={paper.paper_id}>
                  <div className="line-clamp-1 text-sm font-medium">{paper.title}</div>
                  <div className="mt-1 text-xs text-red-700">{paper.error || "解析失败"}</div>
                  <Button className="mt-2" size="sm" variant="outline" onClick={() => void runQuickAction(paper, "parse")}>
                    <RefreshCw className="h-3.5 w-3.5" />
                    重试
                  </Button>
                </div>
              ))
            ) : (
              <div className="rounded-md bg-muted/50 px-3 py-6 text-center text-sm text-muted-foreground">暂无失败任务。</div>
            )}
          </CardContent>
        </Card>
      </section>
    </PageShell>
  );
}

function PaperRow({ busyId, onQuickAction, paper }: { paper: PaperRecord; busyId: string; onQuickAction: (paper: PaperRecord, action: "parse" | "note") => Promise<void> }) {
  const parseBusy = busyId === `parse:${paper.paper_id}`;
  const noteBusy = busyId === `note:${paper.paper_id}`;
  return (
    <div className="grid gap-2 rounded-md px-3 py-2 transition-colors hover:bg-muted/60">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <Link className="truncate text-sm font-medium hover:underline" to={`/library/${encodeURIComponent(paper.paper_id)}`}>
          {paper.title}
        </Link>
        <StatusBadge className="shrink-0" status={derivePaperStatus(paper)} />
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="truncate">{paperSummary(paper)}</span>
        <span className="shrink-0">{formatDate(paper.updated_at)}</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Button asChild size="sm" variant="outline">
          <Link to={`/library/${encodeURIComponent(paper.paper_id)}`}>查看详情</Link>
        </Button>
        <Button size="sm" variant="outline" disabled={parseBusy || !paper.paper_path} onClick={() => void onQuickAction(paper, "parse")}>
          解析 PDF
        </Button>
        <Button asChild size="sm" variant="outline">
          <Link to="/uncategorized">分类</Link>
        </Button>
        <Button size="sm" variant="outline" disabled={noteBusy || paper.parser_status !== "parsed"} onClick={() => void onQuickAction(paper, "note")}>
          <Sparkles className="h-3.5 w-3.5" />
          生成 Note
        </Button>
      </div>
    </div>
  );
}

function CompactPaperRow({ paper }: { paper: PaperRecord }) {
  return (
    <Link className="flex min-w-0 items-center justify-between gap-3 rounded-md px-2 py-1.5 transition-colors hover:bg-muted/60" to={`/library/${encodeURIComponent(paper.paper_id)}`}>
      <div className="min-w-0">
        <div className="truncate text-sm font-medium">{paper.title}</div>
        <div className="truncate text-xs text-muted-foreground">{paperSummary(paper)}</div>
      </div>
    </Link>
  );
}

function ProgressCard({ readProgress, stats, totals }: { readProgress: number; stats: ReturnType<typeof libraryOverviewStats>; totals: Record<string, number> }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">阅读进度</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-end justify-between">
          <div>
            <div className="text-3xl font-semibold">{readProgress}%</div>
            <p className="mt-1 text-sm text-muted-foreground">{totals.processed ?? stats.notes} 已处理 / {totals.papers ?? stats.total} 总量</p>
          </div>
          <CheckCircle2 className="h-6 w-6 text-emerald-600" />
        </div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
          <div className="h-full rounded-full bg-emerald-600" style={{ width: `${readProgress}%` }} />
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
          <span>已解析 {stats.parsed} / 已收录 {totals.library ?? 0}</span>
          <span>已生成 Note {stats.notes} / 已解析 {stats.parsed}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function WorkflowFunnel({ stats, totals }: { stats: ReturnType<typeof libraryOverviewStats>; totals: Record<string, number> }) {
  const rows = [
    ["Discover 候选", totals.curated ?? 0],
    ["已收录", totals.library ?? 0],
    ["已绑定 PDF", Math.max(stats.total - stats.missingPdf, 0)],
    ["已解析", stats.parsed],
    ["已生成 Note", stats.notes],
    ["已审阅", totals.processed ?? stats.notes],
  ] as const;
  const max = Math.max(...rows.map(([, value]) => value), 1);
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">工作流漏斗</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-2">
        {rows.map(([label, value]) => (
          <div className="grid grid-cols-[104px_minmax(0,1fr)_40px] items-center gap-2" key={label}>
            <span className="text-xs text-muted-foreground">{label}</span>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full bg-neutral-600" style={{ width: `${Math.round((value / max) * 100)}%` }} />
            </div>
            <span className="text-right text-xs font-medium">{value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function mergePapers(primary: PaperRecord[], secondary: PaperRecord[]): PaperRecord[] {
  const seen = new Set<string>();
  const merged: PaperRecord[] = [];
  for (const paper of [...primary, ...secondary]) {
    if (seen.has(paper.paper_id)) continue;
    seen.add(paper.paper_id);
    merged.push(paper);
  }
  return merged;
}
