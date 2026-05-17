import { ArrowRight, Bot, Check, Layers, Tags } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/app/EmptyState";
import { PageShell } from "@/components/app/PageShell";
import { BatchActionBar, type BatchAction } from "@/components/common/BatchActionBar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useDialog } from "@/components/ui/DialogProvider";
import { fetchLibraryDashboard, updatePaperClassification, type PaperRecord } from "@/lib/api";
import { formatDate, paperSummary } from "@/lib/format";
import {
  DOMAIN_TREE_SEEDS,
  derivePaperStatus,
  isUncategorizedPaper,
  localClassifySuggestion,
  missingFieldsForPaper,
} from "@/lib/libraryView";
import { cn } from "@/lib/utils";

type ClassificationDraft = {
  domain: string;
  area: string;
  topic: string;
  tags: string;
  confidence: number;
};

export function UncategorizedPage() {
  const { notify } = useDialog();
  const [papers, setPapers] = useState<PaperRecord[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [draft, setDraft] = useState<ClassificationDraft>(emptyDraft());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const payload = await fetchLibraryDashboard();
      const unclassified = payload.data.papers.filter(isUncategorizedPaper);
      setPapers(unclassified);
      setError("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "加载未分类论文失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const selectedPaper = papers.find((paper) => paper.paper_id === selectedPaperId) ?? papers[0] ?? null;
  const progress = useMemo(() => {
    const total = papers.length;
    const done = papers.filter((paper) => !isUncategorizedPaper(paper)).length;
    return { done, total };
  }, [papers]);

  useEffect(() => {
    if (selectedPaper) {
      setSelectedPaperId(selectedPaper.paper_id);
      setDraft({
        domain: selectedPaper.domain,
        area: selectedPaper.area,
        topic: selectedPaper.topic,
        tags: selectedPaper.tags.join(", "),
        confidence: 0,
      });
    }
  }, [selectedPaper?.paper_id]);

  const save = async (next = false) => {
    if (!selectedPaper) return;
    await updatePaperClassification(selectedPaper.paper_id, {
      domain: draft.domain,
      area: draft.area,
      topic: draft.topic,
    });
    await load();
    notify({
      title: "分类已保存",
      message: "Domain、Area、Topic 已写入后端；Tags 等待后端接口接入。",
    });
    if (next) {
      const currentIndex = papers.findIndex((paper) => paper.paper_id === selectedPaper.paper_id);
      const nextPaper = papers[currentIndex + 1] ?? papers[0];
      if (nextPaper) setSelectedPaperId(nextPaper.paper_id);
    }
  };

  const autoSuggest = () => {
    if (!selectedPaper) return;
    const suggestion = localClassifySuggestion(selectedPaper);
    setDraft({
      domain: suggestion.domain,
      area: suggestion.area,
      topic: suggestion.topic,
      tags: suggestion.tags.join(", "),
      confidence: suggestion.confidence,
    });
  };

  const selectedPapers = papers.filter((paper) => selectedIds.has(paper.paper_id));
  const batchActions: BatchAction[] = [
    {
      id: "domain",
      label: "批量设置 Domain",
      icon: <Layers className="h-3.5 w-3.5" />,
      onClick: () => void batchClassify({ domain: draft.domain || "Representation Learning", area: draft.area, topic: draft.topic }),
    },
    {
      id: "area",
      label: "批量设置 Area",
      onClick: () => void batchClassify({ domain: draft.domain || "Representation Learning", area: draft.area || "General", topic: draft.topic }),
    },
    {
      id: "topic",
      label: "批量设置 Topic",
      onClick: () => void batchClassify({ domain: draft.domain || "Representation Learning", area: draft.area || "General", topic: draft.topic || "Representation Learning" }),
    },
    {
      id: "tags",
      label: "批量设置 Tags",
      icon: <Tags className="h-3.5 w-3.5" />,
      disabledReason: "后端尚未提供 Tags 持久化接口。",
      onClick: () => undefined,
    },
  ];

  async function batchClassify(target: { domain: string; area: string; topic: string }) {
    for (const paper of selectedPapers) {
      await updatePaperClassification(paper.paper_id, {
        domain: target.domain || paper.domain,
        area: target.area || paper.area,
        topic: target.topic || paper.topic,
      });
    }
    setSelectedIds(new Set());
    await load();
    notify({ title: "批量分类已完成", message: `已处理 ${selectedPapers.length} 篇论文。` });
  }

  const domains = DOMAIN_TREE_SEEDS.filter((node) => node.level === "domain").map((node) => node.label);

  return (
    <PageShell
      actions={
        <Button asChild size="sm" variant="outline">
          <Link to="/library">
            返回文库
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      }
      description="快速补齐缺少 Domain、Area、Topic 或 Tags 的论文分类信息。"
      title="未分类论文处理"
    >
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

      <Card className="p-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-sm font-medium">处理进度</div>
            <div className="mt-1 text-xs text-muted-foreground">已分类 {progress.done} / 未分类总数 {progress.total}</div>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted md:w-80">
            <div className="h-full rounded-full bg-emerald-600" style={{ width: `${progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : 100}%` }} />
          </div>
        </div>
      </Card>

      <BatchActionBar actions={batchActions} count={selectedIds.size} onClear={() => setSelectedIds(new Set())} />

      {papers.length === 0 && !loading ? (
        <EmptyState description="当前没有未分类论文。" icon={Check} title="分类已完成" />
      ) : (
        <section className="grid min-h-[620px] gap-4 xl:grid-cols-[minmax(420px,1fr)_minmax(320px,0.8fr)_360px]">
          <Card className="overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-10" />
                  <TableHead>Title</TableHead>
                  <TableHead>Venue</TableHead>
                  <TableHead>Year</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead>Missing Fields</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {papers.map((paper) => (
                  <TableRow className={cn("cursor-pointer", selectedPaper?.paper_id === paper.paper_id && "bg-muted/60")} key={paper.paper_id} onClick={() => setSelectedPaperId(paper.paper_id)}>
                    <TableCell onClick={(event) => event.stopPropagation()}>
                      <input
                        checked={selectedIds.has(paper.paper_id)}
                        className="h-4 w-4 rounded border-border"
                        type="checkbox"
                        onChange={() =>
                          setSelectedIds((current) => {
                            const next = new Set(current);
                            if (next.has(paper.paper_id)) next.delete(paper.paper_id);
                            else next.add(paper.paper_id);
                            return next;
                          })
                        }
                      />
                    </TableCell>
                    <TableCell className="max-w-96">
                      <div className="line-clamp-2 font-medium">{paper.title}</div>
                    </TableCell>
                    <TableCell>{paper.venue || "未填写"}</TableCell>
                    <TableCell>{paper.year ?? "未填写"}</TableCell>
                    <TableCell>
                      <StatusBadge status={derivePaperStatus(paper)} />
                    </TableCell>
                    <TableCell>{formatDate(paper.updated_at)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {missingFieldsForPaper(paper).map((field) => (
                          <Badge key={field} variant="warning">
                            缺 {field}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">论文摘要</CardTitle>
            </CardHeader>
            <CardContent>
              {selectedPaper ? (
                <div className="grid gap-3">
                  <h2 className="line-clamp-3 text-lg font-semibold leading-7">{selectedPaper.title}</h2>
                  <p className="text-sm leading-6 text-muted-foreground">{paperSummary(selectedPaper)}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedPaper.tags.length > 0 ? selectedPaper.tags.map((tag) => <Badge key={tag} variant="muted">{tag}</Badge>) : <Badge variant="muted">Tags 未填写</Badge>}
                  </div>
                  <div className="rounded-md bg-muted/50 p-3 text-sm leading-6 text-muted-foreground">
                    当前接口未返回 abstract；这里优先展示本地元数据和推荐摘要，后续可接入 refined/LLM summary。
                  </div>
                </div>
              ) : (
                <EmptyState className="border-0 bg-muted/40" description="选择左侧论文后编辑分类。" icon={Layers} title="未选择论文" />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">分类编辑</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <label className="grid gap-1">
                <span className="text-xs text-muted-foreground">Domain</span>
                <Select value={draft.domain || "none"} onValueChange={(value) => setDraft({ ...draft, domain: value === "none" ? "" : value })}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择 Domain" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">未填写</SelectItem>
                    {domains.map((domain) => (
                      <SelectItem key={domain} value={domain}>
                        {domain}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </label>
              <TextField label="Area" value={draft.area} onChange={(value) => setDraft({ ...draft, area: value })} />
              <TextField label="Topic" value={draft.topic} onChange={(value) => setDraft({ ...draft, topic: value })} />
              <TextField label="Tags" value={draft.tags} onChange={(value) => setDraft({ ...draft, tags: value })} />
              <label className="grid gap-1">
                <span className="text-xs text-muted-foreground">Confidence</span>
                <Input readOnly value={draft.confidence ? `${draft.confidence}%` : "未计算"} />
              </label>
              <div className="grid gap-2">
                <Button size="sm" variant="outline" onClick={autoSuggest}>
                  <Bot className="h-4 w-4" />
                  Auto Suggest
                </Button>
                <Button size="sm" disabled={!selectedPaper} onClick={() => void save(false)}>
                  Save
                </Button>
                <Button size="sm" variant="secondary" disabled={!selectedPaper} onClick={() => void save(true)}>
                  Save and Next
                </Button>
              </div>
              <p className="text-xs leading-5 text-muted-foreground">Auto Suggest 当前使用本地规则建议；AI 分类接口接入后替换此处 TODO。</p>
            </CardContent>
          </Card>
        </section>
      )}
    </PageShell>
  );
}

function TextField({ label, onChange, value }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function emptyDraft(): ClassificationDraft {
  return {
    domain: "",
    area: "",
    topic: "",
    tags: "",
    confidence: 0,
  };
}
