import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  Copy,
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
  Tags,
} from "lucide-react";
import { useState, type ReactNode } from "react";

import { DisabledReasonTooltip } from "@/components/common/DisabledReasonTooltip";
import { EditableMetadata, type EditableMetadataValue } from "@/components/papers/EditableMetadata";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { PaperRecord } from "@/lib/api";
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

const defaultOpen = new Set(["metadata", "status", "paths", "tags"]);

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
          <span className="sr-only">Expand detail panel</span>
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
          <p className="mt-2 text-sm font-medium">Select a paper</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">Metadata, paths, tags, status, and actions will appear here.</p>
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
              <span className="sr-only">Collapse detail panel</span>
            </Button>
          ) : null}
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <LabeledStatus label="PDF" status={pdfStatusForPaper(paper)} />
          <LabeledStatus label="Refine" status={paper.refined_review_status || "not_started"} />
          <LabeledStatus label="Classify" status={paper.classification_status || derivePaperStatus(paper)} />
        </div>
        <DetailActions paper={paper} onGenerateNote={onGenerateNote} onOpenFolder={onOpenFolder} onParsePdf={onParsePdf} />
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        <div className="grid gap-3">
          <Section id="metadata" icon={FileText} open={openSections.has("metadata")} title="Metadata" onToggle={toggle}>
            <EditableMetadata compact classificationOptions={classificationOptions} paper={paper} onSave={onMetadataSave} />
          </Section>

          <Section id="status" icon={Sparkles} open={openSections.has("status")} title="Status" onToggle={toggle}>
            <StatusGrid paper={paper} />
          </Section>

          <Section id="tags" icon={Tags} open={openSections.has("tags")} title="Tags" onToggle={toggle}>
            <TagBlock tags={paper.tags} />
          </Section>

          <Section id="paths" icon={LinkIcon} open={openSections.has("paths")} title="Paths" onToggle={toggle}>
            <PathList paper={paper} />
          </Section>

          <Section id="summary" icon={Sparkles} open={openSections.has("summary")} title="AI Summary" onToggle={toggle}>
            <p className="text-sm leading-6 text-muted-foreground">{paper.summary || "暂无真实 summary。请生成 note/refined 或手动补充 metadata.summary。"}</p>
          </Section>

          <Section id="abstract" icon={FileText} open={openSections.has("summary")} title="Abstract" onToggle={toggle}>
            <p className="text-sm leading-6 text-muted-foreground">{paper.abstract || "暂无真实 abstract。请刷新元数据或手动补充。"}</p>
          </Section>

          <Section id="notes" icon={StickyNote} open={openSections.has("notes")} title="Notes" onToggle={toggle}>
            {paper.note_path ? <PathText value={paper.note_path} /> : <EmptyCopy text="No note has been generated yet." />}
          </Section>

          <Section id="figures" icon={Image} open={openSections.has("figures")} title="Figures" onToggle={toggle}>
            {paper.images_path ? <PathText value={paper.images_path} /> : <EmptyCopy text="No figures path is available." />}
          </Section>

          <Section id="citation" icon={Quote} open={openSections.has("citation")} title="Citation" onToggle={toggle}>
            {paper.doi ? <PathText value={paper.doi} /> : <EmptyCopy text="No DOI or citation metadata is available." />}
          </Section>

          <Section id="related" icon={Network} open={openSections.has("related")} title="Related Papers" onToggle={toggle}>
            <EmptyCopy text="暂无本地相关论文推荐数据。" />
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
  const folderReason = folderDisabledReason(paper, onOpenFolder);

  return (
    <div className="mt-3 grid grid-cols-2 gap-1.5">
      <DisabledReasonTooltip reason={parseReason}>
        <Button className="h-8 px-2 text-xs" size="sm" variant="outline" disabled={Boolean(parseReason)} onClick={() => void onParsePdf?.(paper)}>
          <FileText className="h-3.5 w-3.5" />
          {paper.parser_status === "failed" ? "Retry Parse" : "Parse PDF"}
        </Button>
      </DisabledReasonTooltip>
      <DisabledReasonTooltip reason={noteReason}>
        <Button className="h-8 px-2 text-xs" size="sm" variant="outline" disabled={Boolean(noteReason)} onClick={() => void onGenerateNote?.(paper)}>
          <Sparkles className="h-3.5 w-3.5" />
          Generate Note
        </Button>
      </DisabledReasonTooltip>
      <DisabledReasonTooltip reason={folderReason}>
        <Button className="h-8 px-2 text-xs" size="sm" variant="outline" disabled={Boolean(folderReason)} onClick={() => void onOpenFolder?.(paper)}>
          <FolderOpen className="h-3.5 w-3.5" />
          Open
        </Button>
      </DisabledReasonTooltip>
    </div>
  );
}

function StatusGrid({ paper }: { paper: PaperRecord }) {
  const rows: Array<[string, string]> = [
    ["PDF", pdfStatusForPaper(paper)],
    ["Parser", paper.parser_status || "not_started"],
    ["Refine", paper.refined_review_status || "not_started"],
    ["Classify", paper.classification_status || derivePaperStatus(paper)],
    ["Note", paper.note_status || "missing"],
    ["Note Review", paper.note_review_status || "pending"],
    ["Workflow", paper.workflow_status || derivePaperStatus(paper)],
  ];

  return (
    <div className="grid gap-2">
      {rows.map(([label, status]) => (
        <div className="flex items-center justify-between gap-3" key={label}>
          <span className="text-xs text-muted-foreground">{label}</span>
          <StatusBadge status={status} />
        </div>
      ))}
    </div>
  );
}

function TagBlock({ tags }: { tags: string[] }) {
  if (tags.length === 0) {
    return <Badge variant="muted">No tags</Badge>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((tag) => (
        <Badge key={tag} variant="muted">
          {tag}
        </Badge>
      ))}
    </div>
  );
}

function PathList({ paper }: { paper: PaperRecord }) {
  const rows: Array<[string, string]> = [
    ["Folder", paper.path],
    ["PDF", paper.paper_path],
    ["Note", paper.note_path],
    ["Refined", paper.parser_artifacts.refined_path || paper.refined_path],
    ["Metadata YAML", paper.metadata_path],
    ["Metadata JSON", paper.metadata_json_path],
    ["State", paper.state_path],
  ];

  return (
    <div className="grid gap-2">
      {rows.map(([label, value]) => (
        <div className="grid gap-1" key={label}>
          <span className="text-xs font-medium text-muted-foreground">{label}</span>
          {value ? <PathText value={value} /> : <Badge variant="muted">Missing</Badge>}
        </div>
      ))}
    </div>
  );
}

function LabeledStatus({ label, status }: { label: string; status: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="text-[10px] font-medium uppercase text-muted-foreground">{label}</span>
      <StatusBadge className="px-1.5" status={status} />
    </span>
  );
}

function pdfStatusForPaper(paper: PaperRecord): string {
  return paper.asset_status === "missing_pdf" || !paper.paper_path ? "missing_pdf" : "pdf_ready";
}

function folderDisabledReason(paper: PaperRecord, handler?: (paper: PaperRecord) => Promise<void> | void): string | undefined {
  if (!handler) return "Open folder is not available on this page.";
  if (!paper.path && !paper.paper_path) return "This paper has no local path.";
  return undefined;
}

function parseDisabledReason(paper: PaperRecord, handler?: (paper: PaperRecord) => Promise<void> | void): string | undefined {
  if (!handler) return "Parse action is not connected on this page.";
  if (!paper.paper_path) return "This paper is missing a PDF path.";
  if (!paper.capabilities.parse) return "The current workflow state does not allow parsing.";
  return undefined;
}

function noteDisabledReason(paper: PaperRecord, handler?: (paper: PaperRecord) => Promise<void> | void): string | undefined {
  if (!handler) return "Generate note action is not connected on this page.";
  if (paper.parser_status !== "parsed") return "Parse the PDF before generating a note.";
  if (!paper.capabilities.generate_note) return paper.note_path ? "A note already exists." : "The current workflow state does not allow note generation.";
  return undefined;
}

function Section({
  children,
  icon: Icon,
  id,
  onToggle,
  open,
  title,
}: {
  children: ReactNode;
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
        <span className="sr-only">Copy</span>
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
