import { ArrowLeft, CheckCircle2, Copy, ExternalLink, FileText, FolderOpen, RefreshCw, Sparkles, ThumbsDown, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { EmptyState } from "@/components/app/EmptyState";
import { PageShell } from "@/components/app/PageShell";
import { DisabledReasonTooltip } from "@/components/common/DisabledReasonTooltip";
import { PathCell } from "@/components/common/PathCell";
import { EditableMetadata, type EditableMetadataValue } from "@/components/papers/EditableMetadata";
import { ResponsivePaperInspector } from "@/components/papers/ResponsivePaperInspector";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useDialog } from "@/components/ui/DialogProvider";
import {
  fetchPapersDashboard,
  fetchPaperEvents,
  fetchPaper,
  fetchParserRuns,
  generatePaperNote,
  parsePaperPdf,
  rejectPaper,
  reviewPaperNote,
  reviewPaperRefined,
  updatePaperClassification,
  type PaperEventRecord,
  type PaperRecord,
  type ParserRunRecord,
} from "@/lib/api";
import { formatDate, humanizeStatus, paperSummary } from "@/lib/format";
import { buildClassificationOptions, derivePaperStatus } from "@/lib/libraryView";

export function PaperDetailPage() {
  const { paperId = "" } = useParams();
  const navigate = useNavigate();
  const { confirm, notify } = useDialog();
  const [paper, setPaper] = useState<PaperRecord | null>(null);
  const [libraryPapers, setLibraryPapers] = useState<PaperRecord[]>([]);
  const [runs, setRuns] = useState<ParserRunRecord[]>([]);
  const [events, setEvents] = useState<PaperEventRecord[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false);

  const load = () => {
    if (!paperId) return;
    void Promise.all([fetchPaper(paperId), fetchParserRuns(paperId), fetchPaperEvents(paperId), fetchPapersDashboard().catch(() => null)])
      .then(([paperPayload, runsPayload, eventsPayload, libraryPayload]) => {
        setPaper(paperPayload.data);
        setRuns(runsPayload.data.items);
        setEvents(eventsPayload.data.items);
        setLibraryPapers(libraryPayload?.data.papers ?? []);
        setError("");
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "加载论文详情失败"));
  };

  useEffect(load, [paperId]);

  const runAction = (name: string, task: () => Promise<void>) => {
    setBusy(name);
    void task()
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "执行论文操作失败"))
      .finally(() => setBusy(""));
  };

  const classificationOptions = useMemo(() => buildClassificationOptions(mergeCurrentPaper(libraryPapers, paper)), [libraryPapers, paper]);

  if (!paper) {
    return (
      <PageShell title="论文详情">
        {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : <EmptyState description="正在读取论文元数据。" icon={FileText} title="加载详情" />}
      </PageShell>
    );
  }

  const reasons = disabledReasons(paper, Boolean(busy));

  const deleteCurrentPaper = async () => {
    const accepted = await confirm({
      title: "物理删除这篇论文？",
      message: "将删除论文目录和其中的本地产物，此操作不可恢复。",
      confirmLabel: "物理删除",
      cancelLabel: "取消",
      danger: true,
    });
    if (!accepted) return;

    runAction("delete", async () => {
      await rejectPaper(paper.paper_id);
      navigate("/papers", { replace: true });
    });
  };

  const openFolder = async (target: PaperRecord) => {
    const targetPath = target.path || target.paper_path;
    if (!targetPath) {
      notify({ title: "缺少路径", message: "当前论文没有可打开的本地路径。" });
      return;
    }

    if (window.researchFlow?.openPath) {
      try {
        const result = await window.researchFlow.openPath(targetPath);
        if (!result.ok) {
          await copyPathToClipboard(targetPath);
          notify({ title: "打开文件夹失败，已复制路径", message: result.error || targetPath });
        }
      } catch (err: unknown) {
        await copyPathToClipboard(targetPath);
        notify({ title: "打开文件夹失败，已复制路径", message: err instanceof Error ? err.message : targetPath });
      }
      return;
    }

    await copyPathToClipboard(targetPath);
    notify(electronBridgeMissingMessage(targetPath));
  };

  const saveMetadata = async (value: EditableMetadataValue) => {
    const response = await updatePaperClassification(paper.paper_id, {
      domain: value.domain,
      area: value.area,
      topic: value.topic,
      title: value.title,
      venue: value.venue,
      year: value.year.trim() ? Number(value.year) : null,
      tags: splitTags(value.tags),
      status: value.status,
      paper_path: value.paper_path,
      note_path: value.note_path,
      refined_path: value.refined_path,
    });
    setPaper(response.data);
    if (response.data.paper_id !== paper.paper_id) {
      navigate(`/papers/${encodeURIComponent(response.data.paper_id)}`, { replace: true });
    } else {
      load();
    }
    notify({
      title: "元数据已保存",
      message: "Metadata 已写入后端并刷新当前论文。",
    });
  };

  const reviewRefined = (decision: "approved" | "rejected") => {
    runAction(`review-refined-${decision}`, async () => {
      const response = await reviewPaperRefined(paper.paper_id, { decision });
      setPaper(response.data);
      load();
      notify({
        title: decision === "approved" ? "Refine 已批准" : "Refine 已驳回",
        message: decision === "approved" ? "现在可以生成 LLM note。" : "请修改 refined 后再重新审核。",
      });
    });
  };

  const reviewNote = (decision: "approved" | "rejected") => {
    runAction(`review-note-${decision}`, async () => {
      const response = await reviewPaperNote(paper.paper_id, { decision });
      setPaper(response.data);
      load();
      notify({
        title: decision === "approved" ? "Note 已批准" : "Note 已驳回",
        message: decision === "approved" ? "Note 已通过人工审核。" : "请修改 note 后再重新审核。",
      });
    });
  };

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] min-w-0">
      <PageShell
        actions={
          <Button asChild size="sm" variant="outline">
            <Link to={paper.stage === "library" ? "/papers" : "/discover"}>
              <ArrowLeft className="h-4 w-4" />
              返回
            </Link>
          </Button>
        }
        className="min-w-0 flex-1"
        description={paperSummary(paper)}
        title="论文详情"
      >
        {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

        <Card className="p-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <h1 className="max-w-4xl text-2xl font-semibold leading-8">{paper.title}</h1>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <StatusBadge status={derivePaperStatus(paper)} />
                <StatusBadge status={paper.parser_status} />
                <StatusBadge status={paper.refined_review_status} />
                <StatusBadge status={paper.note_review_status} />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <ActionButton
                disabled={Boolean(busy) || !paper.capabilities.parse}
                icon={<RefreshCw className="h-4 w-4" />}
                label={paper.parser_status === "failed" ? "重试解析" : "解析 PDF"}
                reason={reasons.parse}
                onClick={() =>
                  runAction("parse", async () => {
                    await parsePaperPdf(paper.paper_id, paper.parser_status === "failed");
                    load();
                  })
                }
              />
              <ActionButton
                disabled={Boolean(busy) || !paper.capabilities.generate_note}
                icon={<Sparkles className="h-4 w-4" />}
                label="生成 Note"
                reason={reasons.note}
                onClick={() =>
                  runAction("note", async () => {
                    await generatePaperNote(paper.paper_id, false);
                    load();
                  })
                }
              />
              <ActionButton
                disabled={Boolean(busy) || !paper.capabilities.review_refined}
                icon={<CheckCircle2 className="h-4 w-4" />}
                label="批准 Refine"
                reason={reasons.refined}
                onClick={() => reviewRefined("approved")}
              />
              <ActionButton
                disabled={Boolean(busy) || !paper.capabilities.review_refined}
                icon={<ThumbsDown className="h-4 w-4" />}
                label="驳回 Refine"
                reason={reasons.refined}
                onClick={() => reviewRefined("rejected")}
              />
              <ActionButton
                disabled={Boolean(busy) || !paper.capabilities.review_note}
                icon={<CheckCircle2 className="h-4 w-4" />}
                label="批准 Note"
                reason={reasons.noteReview}
                onClick={() => reviewNote("approved")}
              />
              <ActionButton
                disabled={Boolean(busy) || !paper.capabilities.review_note}
                icon={<ThumbsDown className="h-4 w-4" />}
                label="驳回 Note"
                reason={reasons.noteReview}
                onClick={() => reviewNote("rejected")}
              />
              <DisabledReasonTooltip reason={reasons.delete}>
                <Button size="sm" variant="destructive" disabled={Boolean(busy) || !paper.capabilities.delete} onClick={deleteCurrentPaper}>
                  <Trash2 className="h-4 w-4" />
                  删除
                </Button>
              </DisabledReasonTooltip>
            </div>
          </div>
        </Card>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.8fr)]">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">基本信息</CardTitle>
            </CardHeader>
            <CardContent>
              <EditableMetadata classificationOptions={classificationOptions} paper={paper} onSave={saveMetadata} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between gap-3 space-y-0 pb-3">
              <CardTitle className="text-base">快捷操作</CardTitle>
              <Badge variant="muted">Local</Badge>
            </CardHeader>
            <CardContent className="grid gap-2">
              <Button size="sm" variant="outline" disabled={!paper.path && !paper.paper_path} onClick={() => void openFolder(paper)}>
                <FolderOpen className="h-4 w-4" />
                打开
              </Button>
              <Button size="sm" variant="outline" disabled={!paper.note_path}>
                <ExternalLink className="h-4 w-4" />
                Open Note
              </Button>
              <Button size="sm" variant="outline" onClick={() => void navigator.clipboard?.writeText(`${paper.title}. ${paper.venue || ""} ${paper.year ?? ""}`.trim())}>
                <Copy className="h-4 w-4" />
                Copy Citation
              </Button>
              <p className="text-xs leading-5 text-muted-foreground">Electron 环境会直接打开本地文件夹；Web 环境会复制论文路径。</p>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-4 xl:grid-cols-2">
          <InfoCard
            title="Workflow State"
            rows={[
              ["Workflow", humanizeStatus(paper.workflow_status || derivePaperStatus(paper))],
              ["Stage", paper.stage || "未填写"],
              ["Asset", paper.asset_status || "未填写"],
              ["Parser", paper.parser_status || "未填写"],
              ["Review", paper.review_status || "未填写"],
              ["Refine Review", paper.refined_review_status || "未填写"],
              ["Note Review", paper.note_review_status || "未填写"],
              ["Domain", paper.domain || "未填写"],
              ["Area", paper.area || "未填写"],
              ["Topic", paper.topic || "未填写"],
            ]}
          />
          <ArtifactsCard paper={paper} />
        </section>

        <ParserRunsCard paper={paper} runs={runs} />
        <EventTimelineCard events={events} />

        <section className="grid gap-4 xl:grid-cols-2">
          <TextSection title="AI Summary" text={paper.summary || "暂无真实 summary。请生成 note/refined 或手动补充 metadata.summary。"} />
          <TextSection title="Abstract" text={paper.abstract || "暂无真实 abstract。请刷新元数据或手动补充。"} />
          <TextSection title="Notes" text={paper.note_path ? paper.note_path : "尚未生成 note。"} />
          <TextSection title="Figures" text={paper.images_path ? paper.images_path : "暂无 figures 路径。"} />
          <TextSection title="Related Papers" text="暂无本地相关论文推荐数据。" />
        </section>
      </PageShell>

      <ResponsivePaperInspector
        collapsed={inspectorCollapsed}
        classificationOptions={classificationOptions}
        paper={paper}
        onGenerateNote={(target) =>
          runAction("note", async () => {
            await generatePaperNote(target.paper_id, false);
            load();
          })
        }
        onMetadataSave={saveMetadata}
        onOpenFolder={openFolder}
        onParsePdf={(target) =>
          runAction("parse", async () => {
            await parsePaperPdf(target.paper_id, target.parser_status === "failed");
            load();
          })
        }
        onToggleCollapsed={() => setInspectorCollapsed((value) => !value)}
      />
    </div>
  );
}

function splitTags(value: string): string[] {
  return value
    .split(/[,\n，]/)
    .map((tag) => tag.trim())
    .filter(Boolean);
}

async function copyPathToClipboard(path: string): Promise<void> {
  await navigator.clipboard?.writeText(path);
}

function electronBridgeMissingMessage(targetPath: string): { title: string; message: string } {
  const isElectron = window.researchFlow?.isElectron || navigator.userAgent.includes("Electron");
  if (isElectron) {
    return {
      title: "Electron 打开桥接未加载",
      message: `已复制路径到剪贴板：${targetPath}`,
    };
  }
  return {
    title: "已复制论文文件夹路径",
    message: "当前 Web 环境不能直接打开本地文件夹，路径已复制到剪贴板。",
  };
}

function mergeCurrentPaper(papers: PaperRecord[], paper: PaperRecord | null): PaperRecord[] {
  if (!paper) {
    return papers;
  }
  if (papers.some((item) => item.paper_id === paper.paper_id)) {
    return papers;
  }
  return [...papers, paper];
}

function ActionButton({ disabled, icon, label, onClick, reason }: { label: string; icon?: ReactNode; disabled: boolean; reason?: string; onClick: () => void }) {
  return (
    <DisabledReasonTooltip reason={disabled ? reason : undefined}>
      <Button size="sm" variant="outline" disabled={disabled} onClick={onClick}>
        {icon}
        {label}
      </Button>
    </DisabledReasonTooltip>
  );
}

function disabledReasons(paper: PaperRecord, busy: boolean) {
  if (busy) {
    return {
      parse: "已有任务运行中，请等待当前操作结束。",
      note: "已有任务运行中，请等待当前操作结束。",
      noteReview: "已有任务运行中，请等待当前操作结束。",
      refined: "已有任务运行中，请等待当前操作结束。",
      accept: "已有任务运行中，请等待当前操作结束。",
      delete: "已有任务运行中，请等待当前操作结束。",
    };
  }
  return {
    parse: paper.paper_path ? undefined : "当前论文缺少 PDF，请先下载或绑定 PDF。",
    note: paper.capabilities.generate_note ? undefined : "请先完成 PDF 解析并批准 refined。",
    noteReview: paper.note_path ? undefined : "请先生成 LLM note。",
    refined: paper.parser_status === "parsed" ? undefined : "请先完成 PDF 解析。",
    accept: paper.stage === "library" || paper.review_status === "accepted" ? "当前论文已在文库中。" : undefined,
    delete: paper.capabilities.delete ? undefined : "当前状态不允许删除。",
  };
}

function InfoCard({ rows, title }: { title: string; rows: Array<[string, string]> }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-0">
        {rows.map(([label, value]) => (
          <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-3 border-t py-2 first:border-t-0 first:pt-0 last:pb-0" key={label}>
            <span className="text-sm text-muted-foreground">{label}</span>
            <strong className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-sm" title={value}>
              {value}
            </strong>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ArtifactsCard({ paper }: { paper: PaperRecord }) {
  const rows: Array<[string, string, string]> = [
    ["PDF", paper.paper_path, "缺少 PDF，可从导入或本地绑定入口补齐。"],
    ["Note", paper.note_path, "缺少 Note，可在解析后生成。"],
    ["Refined", paper.parser_artifacts.refined_path || paper.refined_path, "缺少 refined 文档。"],
    ["Parsed text", paper.parser_artifacts.text_path || paper.parsed_text_path, "缺少 parsed text。"],
    ["Sections", paper.parser_artifacts.sections_path || paper.parsed_sections_path, "缺少 sections。"],
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Artifacts</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-0">
        {rows.map(([label, value, empty]) => (
          <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-3 border-t py-2 first:border-t-0 first:pt-0 last:pb-0" key={label}>
            <span className="text-sm text-muted-foreground">{label}</span>
            {value ? <PathCell value={value} /> : <Badge variant="muted">{empty}</Badge>}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ParserRunsCard({ paper, runs }: { paper: PaperRecord; runs: ParserRunRecord[] }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Parser Runs</CardTitle>
      </CardHeader>
      <CardContent>
        {runs.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Status</TableHead>
                <TableHead>Parser</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Finished</TableHead>
                <TableHead>Error</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((run) => (
                <TableRow key={run.run_id}>
                  <TableCell>
                    <StatusBadge status={run.status} />
                  </TableCell>
                  <TableCell>{run.parser}</TableCell>
                  <TableCell>{formatDate(run.started_at)}</TableCell>
                  <TableCell>{formatDate(run.finished_at)}</TableCell>
                  <TableCell className="max-w-sm truncate text-muted-foreground">{run.error || "未填写"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="rounded-md bg-muted/50 px-3 py-6 text-center text-sm text-muted-foreground">
            暂无解析记录，{paper.paper_path ? "可启动解析。" : "绑定 PDF 后可启动解析。"}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EventTimelineCard({ events }: { events: PaperEventRecord[] }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Workflow Log</CardTitle>
      </CardHeader>
      <CardContent>
        {events.length > 0 ? (
          <ol className="grid gap-3">
            {events.map((event, index) => (
              <li className="grid grid-cols-[88px_minmax(0,1fr)] gap-3" key={`${event.timestamp}-${event.event}-${index}`}>
                <time className="pt-0.5 text-xs text-muted-foreground">{formatDate(event.timestamp)}</time>
                <div className="rounded-md border bg-background px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={event.result} />
                    <strong className="text-sm">{event.message || event.event}</strong>
                  </div>
                  {event.next_action ? <p className="mt-1 text-xs text-muted-foreground">{event.next_action}</p> : null}
                  {event.technical_detail ? <p className="mt-2 truncate rounded bg-muted px-2 py-1 text-xs text-muted-foreground">{event.technical_detail}</p> : null}
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <div className="rounded-md bg-muted/50 px-3 py-6 text-center text-sm text-muted-foreground">暂无流程日志，下一次解析、审核或分类操作后会生成记录。</div>
        )}
      </CardContent>
    </Card>
  );
}

function TextSection({ text, title }: { title: string; text: string }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-6 text-muted-foreground">{text}</p>
      </CardContent>
    </Card>
  );
}
