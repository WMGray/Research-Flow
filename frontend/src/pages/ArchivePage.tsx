import { Archive, RotateCcw, SlidersHorizontal } from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/app/EmptyState";
import { FilterSearch } from "@/components/app/FilterSearch";
import { PageShell } from "@/components/app/PageShell";
import { ResponsivePaperInspector } from "@/components/papers/ResponsivePaperInspector";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { fetchHomeDashboard, type PaperRecord } from "@/lib/api";
import { formatDate, paperSummary } from "@/lib/format";

export function ArchivePage() {
  const [papers, setPapers] = useState<PaperRecord[]>([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [selectedPaperId, setSelectedPaperId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    let active = true;

    void fetchHomeDashboard()
      .then((payload) => {
        if (!active) {
          return;
        }
        const allKnown = [...payload.data.recent_papers, ...payload.data.queue_items];
        setPapers(dedupePapers(allKnown).filter((paper) => paper.rejected || paper.status === "rejected"));
        setError("");
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "加载归档失败");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const filtered = useMemo(() => {
    const needle = deferredQuery.trim().toLowerCase();
    return papers.filter((paper) => {
      const text = `${paper.title} ${paper.venue} ${paper.year ?? ""} ${paper.tags.join(" ")}`.toLowerCase();
      const filterMatch = filter === "all" || paper.stage === filter;
      return filterMatch && (!needle || text.includes(needle));
    });
  }, [deferredQuery, filter, papers]);

  const selectedPaper = filtered.find((paper) => paper.paper_id === selectedPaperId) ?? filtered[0] ?? null;

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] min-w-0">
      <PageShell
        actions={
          <Button size="sm" variant="outline" disabled>
            <RotateCcw className="h-4 w-4" />
            恢复所选
          </Button>
        }
        className="min-w-0 flex-1"
        description="前端优先展示归档列表、搜索、筛选和恢复入口；恢复能力等待后端契约接入。"
        title="归档"
      >
        {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

        <section className="flex flex-col gap-3 rounded-lg border bg-card p-3 md:flex-row md:items-center">
          <FilterSearch className="min-w-0 flex-1" label="搜索归档" placeholder="搜索标题、venue、标签..." value={query} onChange={setQuery} />
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-full md:w-40">
              <SelectValue placeholder="范围" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部范围</SelectItem>
              <SelectItem value="discover">发现</SelectItem>
              <SelectItem value="acquire">待处理</SelectItem>
              <SelectItem value="library">文库</SelectItem>
            </SelectContent>
          </Select>
          <Button size="sm" variant="outline" disabled>
            <SlidersHorizontal className="h-4 w-4" />
            更多筛选
          </Button>
        </section>

        {filtered.length > 0 ? (
          <section className="grid gap-2">
            {filtered.map((paper) => (
              <Card
                className={`flex items-center justify-between gap-4 p-3 transition-colors hover:border-neutral-400 ${selectedPaper?.paper_id === paper.paper_id ? "border-neutral-500 bg-muted/30" : ""}`}
                key={paper.paper_id}
                onClick={() => setSelectedPaperId(paper.paper_id)}
              >
                <div className="min-w-0">
                  <div className="line-clamp-1 text-sm font-medium">{paper.title}</div>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>{paperSummary(paper)}</span>
                    <span>{formatDate(paper.updated_at)}</span>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <StatusBadge status={paper.status || "rejected"} />
                  <Button size="sm" variant="outline" disabled>
                    <RotateCcw className="h-4 w-4" />
                    恢复
                  </Button>
                </div>
              </Card>
            ))}
          </section>
        ) : (
          <EmptyState
            description={loading ? "正在读取归档数据。" : "当前没有可展示的归档论文。恢复入口已预留，等待后端契约接入。"}
            icon={Archive}
            title={loading ? "加载中" : "归档为空"}
          />
        )}

        <Badge className="self-start" variant="muted">恢复动作暂不可用</Badge>
      </PageShell>

      <ResponsivePaperInspector paper={selectedPaper} />
    </div>
  );
}

function dedupePapers(papers: PaperRecord[]): PaperRecord[] {
  const seen = new Set<string>();
  const result: PaperRecord[] = [];

  for (const paper of papers) {
    if (seen.has(paper.paper_id)) {
      continue;
    }
    seen.add(paper.paper_id);
    result.push(paper);
  }

  return result;
}
