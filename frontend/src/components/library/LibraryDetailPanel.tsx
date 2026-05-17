import type { ReactNode } from "react";
import {
  Braces,
  ExternalLink,
  FileText,
  FolderOpen,
  MoreHorizontal,
  NotebookText,
  PanelRightClose,
  Plus,
  RefreshCcw,
  Sparkles,
  Star,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { LibraryWorkflowChips } from "@/components/library/LibraryWorkflowChips";
import { ResearchLogCard } from "@/components/library/ResearchLogTimeline";
import {
  buildDetailAuthors,
  buildDetailWorkflow,
  buildEvidenceAbstract,
  buildFileResources,
  buildNotePreview,
  buildNoteStatusRows,
  buildRefinedSummary,
  compactAuthors,
  hasGeneratedNote,
  type DetailTabKey,
} from "@/components/library/paperDetailData";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { PaperContentData, PaperRecord, ResearchLogRecord } from "@/lib/api";
import type { StatusTone } from "@/lib/format";
import { cn } from "@/lib/utils";

type LibraryDetailPanelProps = {
  paper: PaperRecord | null;
  content: PaperContentData | null;
  researchLogs: ResearchLogRecord[];
  starred: boolean;
  width: number;
  onClose: () => void;
  onCreateLog: (paper: PaperRecord) => void;
  onGenerateNote: (paper: PaperRecord) => void;
  onOpenPdf: (paper: PaperRecord) => void;
  onOpenFolder: (paper: PaperRecord) => void;
  onParsePdf: (paper: PaperRecord) => void;
  onToggleStar: (paperId: string) => void;
  onSaveLog: (paper: PaperRecord, log: ResearchLogRecord) => void;
};

type EditableInfo = {
  title: string;
  venue: string;
  year: string;
  authors: string;
  domain: string;
  area: string;
  topic: string;
  doi: string;
  arxiv: string;
  url: string;
  localId: string;
};

const tabs: Array<{ key: DetailTabKey; label: string }> = [
  { key: "overview", label: "概览" },
  { key: "notes", label: "笔记" },
  { key: "info", label: "信息" },
];

export function LibraryDetailPanel({
  onClose,
  content,
  onCreateLog,
  onGenerateNote,
  onOpenPdf,
  onOpenFolder,
  onParsePdf,
  onSaveLog,
  onToggleStar,
  paper,
  researchLogs,
  starred,
  width,
}: LibraryDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<DetailTabKey>("overview");

  useEffect(() => {
    setActiveTab("overview");
  }, [paper?.paper_id]);

  if (!paper) {
    return (
      <aside className="flex h-screen shrink-0 flex-col border-l bg-white" style={{ width }}>
        <div className="grid h-full place-items-center px-8 text-center">
          <div>
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-full border bg-slate-50">
              <PanelRightClose className="h-5 w-5 text-slate-400" />
            </div>
            <h2 className="mt-4 text-sm font-semibold text-slate-800">文献详情</h2>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              选择一篇论文后，这里会显示固定身份区、workflow、摘要、笔记、metadata 和本地文件。
            </p>
          </div>
        </div>
      </aside>
    );
  }

  const generateNote = () => {
    setActiveTab("notes");
    onGenerateNote(paper);
  };

  return (
    <aside className="flex h-screen shrink-0 flex-col border-l bg-white" style={{ width }}>
      <PaperDetailHeader
        paper={paper}
        starred={starred}
        onClose={onClose}
        onGenerateNote={generateNote}
        onOpenFolder={() => onOpenFolder(paper)}
        onOpenPdf={() => onOpenPdf(paper)}
        onParsePdf={() => onParsePdf(paper)}
        onSelectTab={setActiveTab}
        onToggleStar={() => onToggleStar(paper.paper_id)}
      />

      <Tabs className="flex min-h-0 flex-1 flex-col overflow-hidden" value={activeTab} onValueChange={(value) => setActiveTab(value as DetailTabKey)}>
        <div className="border-b px-3 py-2">
          <TabsList className="h-8 w-full rounded bg-slate-100 p-1">
            {tabs.map((tab) => (
              <TabsTrigger className="h-6 flex-1 px-2 text-xs" key={tab.key} value={tab.key}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
          <TabsContent className="mt-0 space-y-4" value="overview">
            <OverviewTab
              content={content}
              logs={researchLogs}
              paper={paper}
              onCreateLog={() => onCreateLog(paper)}
              onOpenFolder={() => onOpenFolder(paper)}
              onOpenPdf={() => onOpenPdf(paper)}
            />
          </TabsContent>
          <TabsContent className="mt-0 space-y-4" value="notes">
            <NotesTab content={content} logs={researchLogs} paper={paper} onCreateLog={() => onCreateLog(paper)} onGenerateNote={generateNote} onOpenFolder={() => onOpenFolder(paper)} onSaveLog={(log) => onSaveLog(paper, log)} />
          </TabsContent>
          <TabsContent className="mt-0 space-y-4" value="info">
            <InfoTab paper={paper} />
          </TabsContent>
        </div>
      </Tabs>
    </aside>
  );
}

function PaperDetailHeader({
  onClose,
  onGenerateNote,
  onOpenFolder,
  onOpenPdf,
  onParsePdf,
  onSelectTab,
  onToggleStar,
  paper,
  starred,
}: {
  paper: PaperRecord;
  starred: boolean;
  onClose: () => void;
  onGenerateNote: () => void;
  onOpenFolder: () => void;
  onOpenPdf: () => void;
  onParsePdf: () => void;
  onSelectTab: (tab: DetailTabKey) => void;
  onToggleStar: () => void;
}) {
  const authors = useMemo(() => buildDetailAuthors(paper), [paper]);
  const identityLine = [paper.venue || "Venue 未填写", paper.year ? String(paper.year) : "Year 未填写", paper.topic || paper.area || "Topic 未填写"].join(" · ");

  return (
    <header className="shrink-0 border-b bg-white px-4 py-3">
      <div className="flex items-start gap-2">
        <button
          aria-label={starred ? "取消星标" : "添加星标"}
          className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded text-slate-400 transition-colors hover:bg-amber-50 hover:text-amber-500"
          type="button"
          onClick={onToggleStar}
        >
          <Star className={cn("h-4 w-4", starred && "fill-amber-400 text-amber-500")} />
        </button>
        <div className="min-w-0 flex-1">
          <h2 className="line-clamp-2 text-sm font-semibold leading-5 text-slate-900" title={paper.title}>
            {paper.title || "Untitled Paper"}
          </h2>
          <div className="mt-1 truncate text-xs text-slate-500" title={identityLine}>
            {identityLine}
          </div>
        </div>
        <Button aria-label="关闭详情" className="h-7 w-7" size="icon" variant="ghost" onClick={onClose}>
          <PanelRightClose className="h-4 w-4" />
        </Button>
      </div>

      <div className="mt-3 grid gap-1 text-xs text-slate-600">
        <HeaderInfoRow label="Authors" value={compactAuthors(authors)} />
        <HeaderInfoRow label="DOI" value={paper.doi || "未填写"} />
        <HeaderInfoRow label="arXiv" value={paper.arxiv_id || "未填写"} />
        <HeaderInfoRow label="URL" value={paper.url || "未填写"} />
      </div>

      <div className="mt-3 flex items-center gap-2">
        <Button className="h-8 flex-1 text-xs" size="sm" variant="outline" onClick={onOpenPdf}>
          <ExternalLink className="h-3.5 w-3.5" />
          打开 PDF
        </Button>
        <Button className="h-8 flex-1 text-xs" size="sm" variant="outline" onClick={onOpenFolder}>
          <FolderOpen className="h-3.5 w-3.5" />
          打开文件夹
        </Button>
        <Button className="h-8 flex-1 text-xs" size="sm" variant="outline" onClick={onGenerateNote}>
          <FileText className="h-3.5 w-3.5" />
          生成 Note
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button aria-label="更多操作" className="h-8 w-8" size="icon" variant="outline">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>更多操作</DropdownMenuLabel>
            <DropdownMenuItem onSelect={onParsePdf}>
              <RefreshCcw className="h-3.5 w-3.5" />
              重新解析
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={onGenerateNote}>
              <FileText className="h-3.5 w-3.5" />
              重新生成 Note
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={onGenerateNote}>
              <Sparkles className="h-3.5 w-3.5" />
              生成 Refined
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => void copyToClipboard(citationText(paper))}>
              复制引用信息
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <LibraryWorkflowChips
        className="mt-3"
        paper={paper}
        onChipClick={(item) => {
          if (item.key === "pdf" && item.status === "PDF 缺失") {
            onSelectTab("overview");
            return;
          }
          if (item.key === "note" || item.status.includes("笔记")) {
            onSelectTab("notes");
            return;
          }
          onSelectTab(item.targetTab);
        }}
      />
    </header>
  );
}

function OverviewTab({
  content,
  logs,
  onCreateLog,
  onOpenFolder,
  onOpenPdf,
  paper,
}: {
  content: PaperContentData | null;
  logs: ResearchLogRecord[];
  paper: PaperRecord;
  onCreateLog: () => void;
  onOpenFolder: () => void;
  onOpenPdf: () => void;
}) {
  const workflow = useMemo(() => buildDetailWorkflow(paper), [paper]);
  const latestLog = logs[0] ?? null;

  return (
    <>
      <FileStatusStrip paper={paper} onOpenFolder={onOpenFolder} onOpenPdf={onOpenPdf} />

      <DetailSection title="摘要">
        <p className="text-xs leading-5 text-slate-600">{content?.abstract || content?.summary || buildEvidenceAbstract(paper)}</p>
      </DetailSection>

      <DetailSection title="工作流时间线">
        <WorkflowTimeline items={workflow} />
      </DetailSection>

      <DetailSection
        action={
          <Button className="h-7 px-2 text-xs" size="sm" variant="outline" onClick={onCreateLog}>
            <Plus className="h-3.5 w-3.5" />
            新建日志
          </Button>
        }
        title="最新研究日志"
      >
        {latestLog ? <ResearchLogCard compact log={latestLog} /> : <p className="text-xs leading-5 text-slate-500">暂无研究日志。</p>}
      </DetailSection>
    </>
  );
}

function NotesTab({
  content,
  logs,
  onCreateLog,
  onGenerateNote,
  onOpenFolder,
  onSaveLog,
  paper,
}: {
  content: PaperContentData | null;
  logs: ResearchLogRecord[];
  paper: PaperRecord;
  onCreateLog: () => void;
  onGenerateNote: () => void;
  onOpenFolder: () => void;
  onSaveLog: (log: ResearchLogRecord) => void;
}) {
  const noteRows = buildNoteStatusRows(paper);
  const notePreview = content?.note_preview ? [content.note_preview] : buildNotePreview(paper);
  const refinedSummary = content?.refined_preview ? [content.refined_preview] : buildRefinedSummary(paper);
  const noteReady = hasGeneratedNote(paper);

  return (
    <>
      <DetailSection title="Note 状态">
        <div className="grid gap-2 text-xs">
          {noteRows.map((row) => (
            <StatusLine key={row.label} label={row.label} meta={row.meta} value={row.value} />
          ))}
        </div>
      </DetailSection>

      <DetailSection title="Note 操作">
        {noteReady ? (
          <div className="grid grid-cols-2 gap-2">
            <Button className="h-8 text-xs" size="sm" variant="outline" onClick={onOpenFolder}>
              打开 Note
            </Button>
            <Button className="h-8 text-xs" size="sm" variant="outline" onClick={onGenerateNote}>
              重新生成 Note
            </Button>
            <Button className="h-8 text-xs" size="sm" variant="outline" onClick={onGenerateNote}>
              生成 Refined
            </Button>
            <Button className="h-8 text-xs" size="sm" variant="outline" onClick={onOpenFolder}>
              在编辑器中打开
            </Button>
          </div>
        ) : (
          <div className="rounded-md border border-dashed bg-slate-50 px-3 py-3">
            <div className="text-xs font-semibold text-slate-800">还没有生成 Note</div>
            <p className="mt-1 text-xs leading-5 text-slate-500">可以基于 metadata、PDF parse 和 abstract 自动生成阅读笔记。</p>
            <Button className="mt-3 h-8 text-xs" size="sm" onClick={onGenerateNote}>
              生成 Note
            </Button>
          </div>
        )}
      </DetailSection>

      <DetailSection title="Note 预览">
        <PreviewBlock paragraphs={notePreview} />
      </DetailSection>

      <DetailSection title="Refined Summary">
        <PreviewBlock paragraphs={refinedSummary} />
      </DetailSection>

      <DetailSection
        action={
          <Button className="h-7 px-2 text-xs" size="sm" variant="outline" onClick={onCreateLog}>
            <Plus className="h-3.5 w-3.5" />
            新建日志
          </Button>
        }
        title="研究日志"
      >
        <div className="space-y-3">
          {logs.length > 0 ? logs.map((log) => (
            <ResearchLogCard key={log.id} log={log} onSave={onSaveLog} />
          )) : <p className="text-xs leading-5 text-slate-500">暂无研究日志。</p>}
        </div>
      </DetailSection>
    </>
  );
}

function InfoTab({ paper }: { paper: PaperRecord }) {
  const authors = buildDetailAuthors(paper);
  const [editableInfo, setEditableInfo] = useState(() => buildEditableInfo(paper, authors));
  const [editableTags, setEditableTags] = useState<string[]>(paper.tags);
  const [tagDraft, setTagDraft] = useState("");
  const [addingTag, setAddingTag] = useState(false);

  useEffect(() => {
    setEditableInfo(buildEditableInfo(paper, authors));
    setEditableTags(paper.tags);
    setTagDraft("");
    setAddingTag(false);
  }, [authors, paper]);

  const addTag = () => {
    const value = tagDraft.trim();
    if (!value || editableTags.includes(value)) return;
    setEditableTags((current) => [...current, value]);
    setTagDraft("");
    setAddingTag(false);
  };

  const updateInfo = (key: keyof EditableInfo, value: string) => {
    setEditableInfo((current) => ({ ...current, [key]: value }));
  };

  const updateTag = (index: number, value: string) => {
    setEditableTags((current) => current.map((tag, itemIndex) => (itemIndex === index ? value : tag)));
  };

  const removeTag = (index: number) => {
    setEditableTags((current) => current.filter((_, itemIndex) => itemIndex !== index));
  };

  return (
    <>
      <DetailSection title="Metadata">
        <div className="grid gap-2 text-xs">
          <EditableInfoRow label="Title" value={editableInfo.title} onChange={(value) => updateInfo("title", value)} />
          <EditableInfoRow label="Venue" value={editableInfo.venue} onChange={(value) => updateInfo("venue", value)} />
          <EditableInfoRow label="Year" value={editableInfo.year} onChange={(value) => updateInfo("year", value)} />
          <EditableInfoRow label="Authors" value={editableInfo.authors} onChange={(value) => updateInfo("authors", value)} />
        </div>
      </DetailSection>

      <DetailSection title="Classification">
        <div className="grid gap-2 text-xs">
          <EditableInfoRow label="Domain" value={editableInfo.domain} onChange={(value) => updateInfo("domain", value)} />
          <EditableInfoRow label="Area" value={editableInfo.area} onChange={(value) => updateInfo("area", value)} />
          <EditableInfoRow label="Topic" value={editableInfo.topic} onChange={(value) => updateInfo("topic", value)} />
        </div>
      </DetailSection>

      <DetailSection title="Tags">
        <div className="flex flex-wrap items-center gap-1.5">
          {editableTags.map((tag, index) => (
            <span className="inline-flex max-w-[12rem] items-center gap-1 rounded-md border bg-slate-50 px-1.5 py-0.5" key={`${tag}-${index}`}>
              <input
                className="min-w-0 bg-transparent px-0.5 py-0.5 text-xs text-slate-700 outline-none"
                size={Math.max(4, Math.min(tag.length || 4, 16))}
                value={tag}
                onChange={(event) => updateTag(index, event.target.value)}
              />
              <button className="grid h-5 w-5 place-items-center rounded text-slate-300 hover:bg-slate-100 hover:text-red-500" type="button" onClick={() => removeTag(index)}>
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          {addingTag ? (
            <span className="inline-flex items-center gap-1 rounded-md border bg-white px-1 py-0.5">
              <input
                autoFocus
                className="h-6 w-24 bg-transparent px-1 text-xs outline-none"
                placeholder="tag"
                value={tagDraft}
                onBlur={() => {
                  if (!tagDraft.trim()) setAddingTag(false);
                }}
                onChange={(event) => setTagDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    addTag();
                  }
                  if (event.key === "Escape") {
                    setTagDraft("");
                    setAddingTag(false);
                  }
                }}
              />
              <button aria-label="取消添加 tag" className="grid h-5 w-5 place-items-center rounded text-slate-400 hover:bg-slate-100" type="button" onClick={() => setAddingTag(false)}>
                <X className="h-3 w-3" />
              </button>
            </span>
          ) : (
            <button aria-label="添加 tag" className="grid h-7 w-7 place-items-center rounded-md border bg-white text-slate-500 hover:bg-slate-50" type="button" onClick={() => setAddingTag(true)}>
              <Plus className="h-3.5 w-3.5" />
            </button>
          )}
          {editableTags.length === 0 && !addingTag ? <span className="text-xs text-slate-500">暂无标签</span> : null}
        </div>
      </DetailSection>

      <DetailSection title="Identifiers">
        <div className="grid gap-2 text-xs">
          <EditableInfoRow label="DOI" value={editableInfo.doi} onChange={(value) => updateInfo("doi", value)} />
          <EditableInfoRow label="arXiv" value={editableInfo.arxiv} onChange={(value) => updateInfo("arxiv", value)} />
          <EditableInfoRow label="URL" value={editableInfo.url} onChange={(value) => updateInfo("url", value)} />
          <EditableInfoRow label="Local ID" value={editableInfo.localId} onChange={(value) => updateInfo("localId", value)} />
        </div>
      </DetailSection>
    </>
  );
}

function FileStatusStrip({
  onOpenFolder,
  onOpenPdf,
  paper,
}: {
  paper: PaperRecord;
  onOpenFolder: () => void;
  onOpenPdf: () => void;
}) {
  const resources = buildFileResources(paper);

  return (
    <section className="grid grid-cols-3 gap-2">
      {resources.map((resource) => {
        const open = resource.id === "pdf" ? onOpenPdf : () => void openResourcePath(resource.path, onOpenFolder);
        const Icon = resourceIcon(resource.id);
        return (
          <button
            className={cn(
              "flex min-w-0 items-center justify-between gap-2 rounded-md border px-2 py-2 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60",
              resourceClassName(resource.id),
            )}
            disabled={!resource.path}
            key={resource.id}
            title={resource.path || "当前文件尚未生成"}
            type="button"
            onClick={open}
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white/70">
              <Icon className="h-3.5 w-3.5" />
            </span>
            <Badge className="h-5 shrink-0 px-1.5 text-[11px]" variant={resource.tone}>
              {resource.status}
            </Badge>
          </button>
        );
      })}
    </section>
  );
}

function resourceIcon(id: "pdf" | "refined" | "note"): LucideIcon {
  if (id === "pdf") return FileText;
  if (id === "refined") return Braces;
  return NotebookText;
}

function resourceClassName(id: "pdf" | "refined" | "note"): string {
  if (id === "pdf") return "border-red-100 bg-red-50 text-red-700 hover:bg-red-100";
  if (id === "refined") return "border-blue-100 bg-blue-50 text-blue-700 hover:bg-blue-100";
  return "border-emerald-100 bg-emerald-50 text-emerald-700 hover:bg-emerald-100";
}

function WorkflowTimeline({ items }: { items: ReturnType<typeof buildDetailWorkflow> }) {
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div className="grid grid-cols-[4.25rem_1fr_auto] items-center gap-2 text-xs" key={item.key}>
          <span className="text-slate-500">{item.label}</span>
          <Badge className="h-5 w-fit px-1.5 text-[11px]" variant={item.tone}>
            {item.status}
          </Badge>
          <span className="whitespace-nowrap text-[11px] text-slate-400">{item.timestamp}</span>
        </div>
      ))}
    </div>
  );
}

function DetailSection({ action, children, title }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="border-b border-slate-100 pb-4 last:border-0">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        {action}
      </div>
      {children}
    </section>
  );
}

function HeaderInfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 gap-2">
      <span className="w-12 shrink-0 text-slate-400">{label}</span>
      <span className="min-w-0 truncate text-slate-700" title={value}>
        {value}
      </span>
    </div>
  );
}

function KeyValueRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[5.5rem_1fr] gap-2">
      <span className="text-slate-400">{label}</span>
      <span className="min-w-0 text-slate-700">{value || "未填写"}</span>
    </div>
  );
}

function EditableInfoRow({ label, onChange, value }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="grid grid-cols-[5.5rem_1fr] gap-2">
      <span className="pt-1 text-slate-400">{label}</span>
      <input
        className="min-w-0 rounded border-transparent bg-transparent px-1 py-1 text-slate-700 outline-none hover:border-slate-200 focus:border-blue-200 focus:bg-white"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function buildEditableInfo(paper: PaperRecord, authors: string[]): EditableInfo {
  return {
    title: paper.title || "未填写",
    venue: paper.venue || "未填写",
    year: paper.year ? String(paper.year) : "未填写",
    authors: compactAuthors(authors),
    domain: paper.domain || "未填写",
    area: paper.area || "未填写",
    topic: paper.topic || "未填写",
    doi: paper.doi || "未填写",
    arxiv: paper.arxiv_id || "未填写",
    url: paper.url || "未填写",
    localId: paper.slug || paper.paper_id || "未填写",
  };
}

function StatusLine({ label, meta, tone = "muted", value }: { label: string; value: string; meta?: string; tone?: StatusTone }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded border bg-slate-50 px-2 py-1.5">
      <span className="text-slate-500">{label}</span>
      <div className="min-w-0 text-right">
        <Badge className="h-5 px-1.5 text-[11px]" variant={tone}>
          {value}
        </Badge>
        {meta ? <div className="mt-0.5 text-[11px] text-slate-400">{meta}</div> : null}
      </div>
    </div>
  );
}

function PreviewBlock({ paragraphs }: { paragraphs: string[] }) {
  return (
    <div className="rounded-md border bg-slate-50 px-3 py-3 font-mono text-[11px] leading-5 text-slate-700">
      {paragraphs.map((paragraph) => (
        <p className="mb-2 whitespace-pre-line last:mb-0" key={paragraph}>
          {paragraph}
        </p>
      ))}
    </div>
  );
}

function citationText(paper: PaperRecord): string {
  const year = paper.year ? ` (${paper.year}).` : ".";
  return `${paper.title}${year} ${paper.venue || ""}`.trim();
}

async function copyToClipboard(value: string): Promise<void> {
  if (!value) return;
  await navigator.clipboard?.writeText(value);
}

async function openResourcePath(path: string, fallback: () => void): Promise<void> {
  if (!path) return;
  if (window.researchFlow?.openPath) {
    const result = await window.researchFlow.openPath(path);
    if (result.ok) return;
  }
  await copyToClipboard(path);
  fallback();
}
