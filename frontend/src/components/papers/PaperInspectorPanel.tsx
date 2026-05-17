import { BookOpen, FileText, Image, LinkIcon, Network, Quote, Sparkles, StickyNote } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { PaperRecord } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type PaperInspectorPanelProps = {
  paper: PaperRecord | null;
  className?: string;
  onClose?: () => void;
};

export function PaperInspectorPanel({ className, onClose, paper }: PaperInspectorPanelProps) {
  return (
    <aside className={cn("hidden w-84 shrink-0 border-l bg-card xl:block", className)}>
      <PaperInspectorContent onClose={onClose} paper={paper} />
    </aside>
  );
}

export function PaperInspectorContent({ onClose, paper }: PaperInspectorPanelProps) {
  if (!paper) {
    return (
      <div className="grid h-full place-items-center p-6 text-center">
        <div>
          <BookOpen className="mx-auto h-5 w-5 text-muted-foreground" />
          <p className="mt-2 text-sm font-medium">选择一篇论文</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">元数据、AI summary、notes 和引用信息会显示在这里。</p>
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
          {onClose ? (
            <Button size="sm" variant="ghost" onClick={onClose}>
              关闭
            </Button>
          ) : null}
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <StatusBadge status={paper.review_status || paper.status} />
          <StatusBadge status={paper.parser_status} />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        <div className="grid gap-4">
          <DetailBlock icon={FileText} title="Metadata">
            <MetaRow label="Venue" value={paper.venue || "-"} />
            <MetaRow label="Year" value={paper.year ? String(paper.year) : "-"} />
            <MetaRow label="Domain" value={paper.domain || "-"} />
            <MetaRow label="Area" value={paper.area || "-"} />
            <MetaRow label="Topic" value={paper.topic || "-"} />
            <MetaRow label="Updated" value={formatDate(paper.updated_at)} />
          </DetailBlock>

          <DetailBlock icon={Sparkles} title="AI Summary">
            <p className="text-sm leading-6 text-muted-foreground">{paper.summary || "暂无真实 summary。请生成 note/refined 或手动补充 metadata.summary。"}</p>
          </DetailBlock>

          <DetailBlock icon={FileText} title="Abstract">
            <p className="text-sm leading-6 text-muted-foreground">{paper.abstract || "暂无真实 abstract。请刷新元数据或手动补充。"}</p>
          </DetailBlock>

          <DetailBlock icon={StickyNote} title="Notes">
            {paper.note_path ? <PathText value={paper.note_path} /> : <EmptyCopy text="尚未生成 note。" />}
          </DetailBlock>

          <DetailBlock icon={Image} title="Figures">
            {paper.images_path ? <PathText value={paper.images_path} /> : <EmptyCopy text="暂无 figures 路径。" />}
          </DetailBlock>

          <DetailBlock icon={Quote} title="Citation">
            {paper.doi ? <PathText value={paper.doi} /> : <EmptyCopy text="暂无 DOI 或引用信息。" />}
          </DetailBlock>

          <DetailBlock icon={Network} title="Related Papers">
            <EmptyCopy text="暂无本地相关论文推荐数据。" />
          </DetailBlock>
        </div>
      </div>
    </div>
  );
}

function DetailBlock({
  children,
  icon: Icon,
  title,
}: {
  children: React.ReactNode;
  icon: typeof FileText;
  title: string;
}) {
  return (
    <Card className="p-3">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium">
        <Icon className="h-4 w-4 text-muted-foreground" />
        {title}
      </div>
      {children}
    </Card>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 border-t py-2 first:border-t-0 first:pt-0 last:pb-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="max-w-44 overflow-hidden text-ellipsis text-right text-xs font-medium">{value}</span>
    </div>
  );
}

function PathText({ value }: { value: string }) {
  return (
    <div className="flex items-start gap-2 rounded-md bg-muted/60 p-2 text-xs leading-5 text-muted-foreground">
      <LinkIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span className="break-all">{value}</span>
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
