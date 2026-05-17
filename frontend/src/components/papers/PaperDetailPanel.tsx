import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  Copy,
  Download,
  FileText,
  FolderOpen,
  Image,
  LinkIcon,
  Network,
  PanelRightClose,
  PanelRightOpen,
  Quote,
  Sparkles,
  StickyNote,
} from "lucide-react";
import { useState } from "react";

import { DisabledReasonTooltip } from "@/components/common/DisabledReasonTooltip";
import { EditableMetadata, type EditableMetadataValue } from "@/components/papers/EditableMetadata";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { PaperRecord } from "@/lib/api";
import { formatDate, paperSummary } from "@/lib/format";
import { derivePaperStatus, type ClassificationOptionSet } from "@/lib/libraryView";
import { cn } from "@/lib/utils";

type PaperDetailPanelProps = {
  paper: PaperRecord | null;
  collapsed?: boolean;
  className?: string;
  width?: number;
  classificationOptions?: ClassificationOptionSet;
  onToggleCollapsed?: () => void;
  onMetadataSave?: (value: EditableMetadataValue) => Promise<void> | void;
  onGenerateNote?: (paper: PaperRecord) => Promise<void> | void;
  onParsePdf?: (paper: PaperRecord) => Promise<void> | void;
  onOpenFolder?: (paper: PaperRecord) => Promise<void> | void;
};

const defaultOpen = new Set(["metadata", "summary", "notes"]);

export function PaperDetailPanel({
  className,
  classificationOptions,
  collapsed = false,
  onGenerateNote,
  onMetadataSave,
  onOpenFolder,
  onParsePdf,
  onToggleCollapsed,
  paper,
  width,
}: PaperDetailPanelProps) {
  if (collapsed) {
    return (
      <aside className={cn("hidden w-12 shrink-0 border-l bg-card xl:flex xl:flex-col xl:items-center xl:py-3", className)}>
        <Button size="icon" variant="ghost" onClick={onToggleCollapsed}>
          <PanelRightOpen className="h-4 w-4" />
          <span className="sr-only">展开详情栏</span>
        </Button>
      </aside>
    );
  }

  return (
    <aside className={cn("hidden shrink-0 border-l bg-card xl:block", className)} style={{ width: width ?? 390 }}>
      <PaperDetailContent
        classificationOptions={classificationOptions}
        onGenerateNote={onGenerateNote}
        onMetadataSave={onMetadataSave}
        onOpenFolder={onOpenFolder}
        onParsePdf={onParsePdf}
        onToggleCollapsed={onToggleCollapsed}
        paper={paper}
      />
    </aside>
  );
}

export function PaperDetailContent({ classificationOptions, onGenerateNote, onMetadataSave, onOpenFolder, onParsePdf, onToggleCollapsed, paper }: PaperDetailPanelProps) {
  const [openSections, setOpenSections] = useState(defaultOpen);

  const toggle = (id: string) => {
    setOpenSections((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  if (!paper) {
    return (
      <div className="grid h-full place-items-center p-6 text-center">
        <div>
          <BookOpen className="mx-auto h-5 w-5 text-muted-foreground" />
          <p className="mt-2 text-sm font-medium">选择一篇论文</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">元数据、AI summary、notes、figures 和 citation 会显示在这里。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-xs font-medium uppercase text-muted-foreground">Paper Detail</div>
            <h2 className="mt-2 line-clamp-3 text-base font-semibold leading-6">{paper.title}</h2>
          </div>
          {onToggleCollapsed ? (
            <Button size="icon" variant="ghost" onClick={onToggleCollapsed}>
              <PanelRightClose className="h-4 w-4" />
              <span className="sr-only">折叠详情栏</span>
            </Button>
          ) : null}
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <StatusBadge status={derivePaperStatus(paper)} />
          <StatusBadge status={paper.parser_status} />
        </div>
        <DetailActions paper={paper} onGenerateNote={onGenerateNote} onOpenFolder={onOpenFolder} onParsePdf={onParsePdf} />
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        <div className="grid gap-3">
          <Section id="metadata" icon={FileText} open={openSections.has("metadata")} title="Metadata" onToggle={toggle}>
            <EditableMetadata compact classificationOptions={classificationOptions} paper={paper} onSave={onMetadataSave} />
          </Section>

          <Section id="summary" icon={Sparkles} open={openSections.has("summary")} title="AI Summary" onToggle={toggle}>
            <p className="text-sm leading-6 text-muted-foreground">{paperSummary(paper)}。当前接口未返回完整 AI summary，解析完成后可在 note 或 refined 文档中扩展展示。</p>
          </Section>

          <Section id="notes" icon={StickyNote} open={openSections.has("notes")} title="Notes" onToggle={toggle}>
            {paper.note_path ? <PathText value={paper.note_path} /> : <EmptyCopy text="尚未生成 note。" />}
          </Section>

          <Section id="figures" icon={Image} open={openSections.has("figures")} title="Figures" onToggle={toggle}>
            {paper.images_path ? <PathText value={paper.images_path} /> : <EmptyCopy text="暂无 figures 路径。" />}
          </Section>

          <Section id="citation" icon={Quote} open={openSections.has("citation")} title="Citation" onToggle={toggle}>
            {paper.doi ? <PathText value={paper.doi} /> : <EmptyCopy text="暂无 DOI 或引用信息。" />}
          </Section>

          <Section id="related" icon={Network} open={openSections.has("related")} title="Related Papers" onToggle={toggle}>
            <EmptyCopy text="相关论文关系暂未接入。" />
          </Section>
        </div>
      </div>
    </div>
  );
}

function DetailActions({
  onGenerateNote,
  onOpenFolder,
  onParsePdf,
  paper,
}: {
  paper: PaperRecord;
  onGenerateNote?: (paper: PaperRecord) => Promise<void> | void;
  onOpenFolder?: (paper: PaperRecord) => Promise<void> | void;
  onParsePdf?: (paper: PaperRecord) => Promise<void> | void;
}) {
  const parseReason = parseDisabledReason(paper, onParsePdf);
  const noteReason = noteDisabledReason(paper, onGenerateNote);
  const downloadReason = downloadDisabledReason(paper);
  const folderReason = folderDisabledReason(paper, onOpenFolder);

  return (
    <div className="mt-3 grid grid-cols-2 gap-1.5">
      <DisabledReasonTooltip reason={parseReason}>
        <Button className="h-8 px-2 text-xs" size="sm" variant="outline" disabled={Boolean(parseReason)} onClick={() => void onParsePdf?.(paper)}>
          <FileText className="h-3.5 w-3.5" />
          {paper.parser_status === "failed" ? "重试解析" : "解析 PDF"}
        </Button>
      </DisabledReasonTooltip>
      <DisabledReasonTooltip reason={noteReason}>
        <Button className="h-8 px-2 text-xs" size="sm" variant="outline" disabled={Boolean(noteReason)} onClick={() => void onGenerateNote?.(paper)}>
          <Sparkles className="h-3.5 w-3.5" />
          生成 Note
        </Button>
      </DisabledReasonTooltip>
      <DisabledReasonTooltip reason={folderReason}>
        <Button className="h-8 px-2 text-xs" size="sm" variant="outline" disabled={Boolean(folderReason)} onClick={() => void onOpenFolder?.(paper)}>
          <FolderOpen className="h-3.5 w-3.5" />
          打开
        </Button>
      </DisabledReasonTooltip>
      <DisabledReasonTooltip reason={downloadReason}>
        <Button className="h-8 px-2 text-xs" size="sm" variant="outline" disabled>
          <Download className="h-3.5 w-3.5" />
          下载 PDF
        </Button>
      </DisabledReasonTooltip>
    </div>
  );
}

function folderDisabledReason(paper: PaperRecord, handler?: (paper: PaperRecord) => Promise<void> | void): string | undefined {
  if (!handler) return "当前页面尚未接入打开文件夹动作。";
  if (!paper.path && !paper.paper_path) return "当前论文缺少本地路径。";
  return undefined;
}

function parseDisabledReason(paper: PaperRecord, handler?: (paper: PaperRecord) => Promise<void> | void): string | undefined {
  if (!handler) return "当前页面尚未接入解析动作。";
  if (!paper.paper_path) return "当前论文缺少 PDF，请先下载或在 Metadata 中绑定 PDF Path。";
  if (!paper.capabilities.parse) return "当前论文状态不允许解析，可能正在解析或不在可解析阶段。";
  return undefined;
}

function noteDisabledReason(paper: PaperRecord, handler?: (paper: PaperRecord) => Promise<void> | void): string | undefined {
  if (!handler) return "当前页面尚未接入生成 Note 动作。";
  if (paper.parser_status !== "parsed") return "请先完成 PDF 解析。";
  if (!paper.capabilities.generate_note) return paper.note_path ? "当前论文已存在 Note。" : "当前论文状态不允许生成 Note。";
  return undefined;
}

function downloadDisabledReason(paper: PaperRecord): string {
  if (paper.paper_path) return "本地已绑定 PDF；下载/重新下载需要后端下载接口或 Electron 本地桥接。";
  return "后端尚未提供下载 PDF 接口；请先通过导入或 Metadata 绑定 PDF Path。";
}

function Section({
  children,
  icon: Icon,
  id,
  onToggle,
  open,
  title,
}: {
  children: React.ReactNode;
  icon: typeof FileText;
  id: string;
  open: boolean;
  title: string;
  onToggle: (id: string) => void;
}) {
  return (
    <Card className="p-3">
      <button className="flex w-full items-center justify-between gap-2 text-sm font-medium" type="button" onClick={() => onToggle(id)}>
        <span className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {title}
        </span>
        {open ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
      </button>
      {open ? <div className="mt-3">{children}</div> : null}
    </Card>
  );
}

function PathText({ value }: { value: string }) {
  const copy = async () => {
    await navigator.clipboard?.writeText(value);
  };

  return (
    <div className="flex items-start gap-2 rounded-md bg-muted/60 p-2 text-xs leading-5 text-muted-foreground">
      <LinkIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span className="min-w-0 flex-1 break-all">{value}</span>
      <Button className="h-6 w-6 shrink-0" size="icon" variant="ghost" onClick={copy}>
        <Copy className="h-3.5 w-3.5" />
        <span className="sr-only">复制</span>
      </Button>
    </div>
  );
}

function EmptyCopy({ text }: { text: string }) {
  return (
    <>
      <Separator className="mb-3" />
      <Badge variant="muted">{text}</Badge>
    </>
  );
}

export type { EditableMetadataValue };
