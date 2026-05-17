import { Link } from "react-router-dom";

import { DisabledReasonTooltip } from "@/components/common/DisabledReasonTooltip";
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
  { key: "title", label: "Title", className: "min-w-[420px]" },
  { key: "venue", label: "Venue" },
  { key: "year", label: "Year" },
  { key: "tags", label: "Tags" },
  { key: "status", label: "Status" },
  { key: "updated", label: "Updated" },
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
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead className="w-10">
            <input aria-label="全选论文" checked={allSelected} className="h-4 w-4 rounded border-border" type="checkbox" onChange={onToggleAll} />
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
                aria-label={`选择 ${paper.title}`}
                checked={selectedIds.has(paper.paper_id)}
                className="h-4 w-4 rounded border-border"
                type="checkbox"
                onChange={() => onToggleSelection(paper.paper_id)}
              />
            </TableCell>
            <TableCell>
              <div className="max-w-[640px] min-w-0">
                <Link className="line-clamp-2 block max-w-full font-medium leading-5 hover:underline" to={`/library/${encodeURIComponent(paper.paper_id)}`} title={paper.title}>
                  {paper.title}
                </Link>
                <div className="line-clamp-1 text-xs text-muted-foreground">{paper.venue || "未填写"} · {paper.year ?? "未填写"} · {paper.path}</div>
              </div>
            </TableCell>
            <TableCell className="max-w-36 truncate">{paper.venue || "未填写"}</TableCell>
            <TableCell>{paper.year ?? "未填写"}</TableCell>
            <TableCell>
              <TagList tags={paper.tags.length > 0 ? paper.tags : [paper.topic || paper.area || paper.domain].filter(Boolean)} />
            </TableCell>
            <TableCell>
              <StatusBadge status={derivePaperStatus(paper)} />
            </TableCell>
            <TableCell className="text-muted-foreground">{formatDate(paper.updated_at)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function TagList({ tags }: { tags: string[] }) {
  if (tags.length === 0) {
    return <span className="text-xs text-muted-foreground">未填写</span>;
  }
  const visible = tags.slice(0, 3);
  const hidden = tags.length - visible.length;
  return (
    <div className="flex max-w-56 flex-wrap gap-1">
      {visible.map((tag) => (
        <Badge key={tag} variant="muted">
          {tag}
        </Badge>
      ))}
      {hidden > 0 ? <Badge variant="outline">+{hidden}</Badge> : null}
    </div>
  );
}
