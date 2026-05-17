import { Link } from "react-router-dom";

import { SortableHeader } from "@/components/common/SortableHeader";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { PaperRecord } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { derivePaperStatus, type SortKey, type SortState } from "@/lib/libraryView";
import { cn } from "@/lib/utils";

type PaperTableProps = {
  papers: PaperRecord[];
  selectedPaperId: string;
  selectedIds: Set<string>;
  sort: SortState;
  onSelectPaper: (paper: PaperRecord) => void;
  onToggleSelection: (paperId: string) => void;
  onToggleAll: () => void;
  onSort: (key: SortKey) => void;
};

const columns: Array<{ key: SortKey; label: string; className?: string }> = [
  { key: "title", label: "Title", className: "min-w-[520px]" },
  { key: "tags", label: "Tags", className: "w-56" },
  { key: "status", label: "Status", className: "w-72" },
  { key: "updated", label: "Updated", className: "w-28" },
];

const PAPER_DRAG_TYPE = "application/x-research-flow-paper-id";

export function PaperTable({
  onSelectPaper,
  onSort,
  onToggleAll,
  onToggleSelection,
  papers,
  selectedIds,
  selectedPaperId,
  sort,
}: PaperTableProps) {
  const allSelected = papers.length > 0 && papers.every((paper) => selectedIds.has(paper.paper_id));

  return (
    <Table className="min-w-[1120px] table-fixed">
      <colgroup>
        <col className="w-10" />
        <col />
        <col className="w-56" />
        <col className="w-72" />
        <col className="w-28" />
      </colgroup>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead className="w-10">
            <input aria-label="Select all papers" checked={allSelected} className="h-4 w-4 rounded border-border" type="checkbox" onChange={onToggleAll} />
          </TableHead>
          {columns.map((column) => (
            <TableHead className={column.className} key={column.key}>
              <SortableHeader activeKey={sort.key} direction={sort.direction} label={column.label} sortKey={column.key} onSort={onSort} />
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {papers.map((paper) => (
          <TableRow
            className={cn("cursor-pointer", selectedPaperId === paper.paper_id && "bg-muted/60")}
            draggable
            key={paper.paper_id}
            onDragStart={(event) => {
              event.dataTransfer.effectAllowed = "move";
              event.dataTransfer.setData(PAPER_DRAG_TYPE, paper.paper_id);
              event.dataTransfer.setData("text/plain", paper.paper_id);
            }}
            onClick={() => onSelectPaper(paper)}
          >
            <TableCell onClick={(event) => event.stopPropagation()}>
              <input
                aria-label={`Select ${paper.title}`}
                checked={selectedIds.has(paper.paper_id)}
                className="h-4 w-4 rounded border-border"
                type="checkbox"
                onChange={() => onToggleSelection(paper.paper_id)}
              />
            </TableCell>
            <TableCell>
              <div className="min-w-0">
                <Link className="line-clamp-2 block max-w-full font-medium leading-5 hover:underline" to={`/library/${encodeURIComponent(paper.paper_id)}`} title={paper.title}>
                  {paper.title}
                </Link>
                <div className="line-clamp-1 text-xs text-muted-foreground">{paperSubtitle(paper)}</div>
              </div>
            </TableCell>
            <TableCell>
              <TagList tags={paper.tags} />
            </TableCell>
            <TableCell>
              <StatusList paper={paper} />
            </TableCell>
            <TableCell className="text-muted-foreground">{formatDate(paper.updated_at)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function paperSubtitle(paper: PaperRecord): string {
  return [
    paper.venue || "No venue",
    paper.year ? String(paper.year) : "No year",
    paper.area || "No area",
    paper.topic || "No topic",
  ].join(" / ");
}

function StatusList({ paper }: { paper: PaperRecord }) {
  const pdfStatus = paper.asset_status === "missing_pdf" || !paper.paper_path ? "missing_pdf" : "pdf_ready";
  const refineStatus = paper.refined_review_status || "not_started";
  const classifyStatus = paper.classification_status || derivePaperStatus(paper);

  return (
    <div className="flex flex-wrap gap-1.5">
      <LabeledStatus label="PDF" status={pdfStatus} />
      <LabeledStatus label="Refine" status={refineStatus} />
      <LabeledStatus label="Classify" status={classifyStatus} />
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

function TagList({ tags }: { tags: string[] }) {
  if (tags.length === 0) {
    return <span className="text-xs text-muted-foreground">No tags</span>;
  }
  const visible = tags.slice(0, 3);
  const hidden = tags.length - visible.length;
  return (
    <div className="flex max-w-52 flex-wrap gap-1">
      {visible.map((tag) => (
        <Badge className="max-w-28 truncate" key={tag} variant="muted">
          {tag}
        </Badge>
      ))}
      {hidden > 0 ? <Badge variant="outline">+{hidden}</Badge> : null}
    </div>
  );
}
