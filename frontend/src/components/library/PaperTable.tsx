import { Star } from "lucide-react";

import { SortableHeader } from "@/components/common/SortableHeader";
import { LibraryWorkflowChips } from "@/components/library/LibraryWorkflowChips";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { PaperRecord } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { paperSubtitle } from "@/lib/libraryWorkspace";
import type { SortKey, SortState } from "@/lib/libraryView";
import { cn } from "@/lib/utils";

type PaperTableProps = {
  papers: PaperRecord[];
  selectedPaperId: string;
  selectedIds: Set<string>;
  starredIds: Set<string>;
  sort: SortState;
  onSelectPaper: (paper: PaperRecord) => void;
  onToggleSelection: (paperId: string) => void;
  onToggleAll: () => void;
  onToggleStar: (paperId: string) => void;
  onSort: (key: SortKey) => void;
};

const columns: Array<{ key: SortKey; label: string; className?: string }> = [
  { key: "title", label: "标题 / 期刊 / 年份", className: "min-w-[520px]" },
  { key: "tags", label: "标签", className: "w-48" },
  { key: "status", label: "工作流", className: "w-64" },
  { key: "updated", label: "更新日期", className: "w-28" },
];

const PAPER_DRAG_TYPE = "application/x-research-flow-paper-id";

export function PaperTable({
  onSelectPaper,
  onSort,
  onToggleAll,
  onToggleSelection,
  onToggleStar,
  papers,
  selectedIds,
  selectedPaperId,
  sort,
  starredIds,
}: PaperTableProps) {
  const allSelected = papers.length > 0 && papers.every((paper) => selectedIds.has(paper.paper_id));

  return (
    <Table className="min-w-[1180px] table-fixed text-xs">
      <colgroup>
        <col className="w-9" />
        <col className="w-8" />
        <col />
        <col className="w-48" />
        <col className="w-64" />
        <col className="w-28" />
      </colgroup>
      <TableHeader>
        <TableRow className="h-8 border-slate-200 bg-slate-50 hover:bg-slate-50">
          <TableHead className="w-9 px-2">
            <input aria-label="Select all papers" checked={allSelected} className="h-3.5 w-3.5 rounded border-slate-300" type="checkbox" onChange={onToggleAll} />
          </TableHead>
          <TableHead className="w-8 px-1">
            <span className="sr-only">星标</span>
          </TableHead>
          {columns.map((column) => (
            <TableHead className={cn("h-8 px-2 text-[11px] uppercase tracking-wide text-slate-500", column.className)} key={column.key}>
              <SortableHeader activeKey={sort.key} direction={sort.direction} label={column.label} sortKey={column.key} onSort={onSort} />
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {papers.map((paper) => {
          const selected = selectedPaperId === paper.paper_id;
          const starred = starredIds.has(paper.paper_id);
          return (
            <TableRow
              className={cn(
                "h-12 cursor-pointer border-slate-100 transition-colors hover:bg-slate-50",
                selected && "bg-blue-50/80 hover:bg-blue-50",
              )}
              draggable
              key={paper.paper_id}
              onClick={() => onSelectPaper(paper)}
              onDragStart={(event) => {
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData(PAPER_DRAG_TYPE, paper.paper_id);
                event.dataTransfer.setData("text/plain", paper.paper_id);
              }}
            >
              <TableCell className="px-2" onClick={(event) => event.stopPropagation()}>
                <input
                  aria-label={`Select ${paper.title}`}
                  checked={selectedIds.has(paper.paper_id)}
                  className="h-3.5 w-3.5 rounded border-slate-300"
                  type="checkbox"
                  onChange={() => onToggleSelection(paper.paper_id)}
                />
              </TableCell>
              <TableCell className="px-1" onClick={(event) => event.stopPropagation()}>
                <button aria-label={starred ? "取消星标" : "添加星标"} className="grid h-6 w-6 place-items-center rounded text-slate-300 hover:bg-amber-50 hover:text-amber-500" type="button" onClick={() => onToggleStar(paper.paper_id)}>
                  <Star className={cn("h-3.5 w-3.5", starred && "fill-amber-400 text-amber-500")} />
                </button>
              </TableCell>
              <TableCell className="px-2">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium leading-5 text-slate-900" title={paper.title}>
                    {paper.title}
                  </div>
                  <div className="truncate text-[11px] leading-4 text-slate-500">{paperSubtitle(paper)}</div>
                </div>
              </TableCell>
              <TableCell className="px-2">
                <TagList tags={paper.tags} />
              </TableCell>
              <TableCell className="px-2">
                <LibraryWorkflowChips paper={paper} maxVisible={3} />
              </TableCell>
              <TableCell className="whitespace-nowrap px-2 text-[11px] text-slate-500">{formatDate(paper.updated_at)}</TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

function TagList({ tags }: { tags: string[] }) {
  if (tags.length === 0) {
    return <span className="text-[11px] text-slate-400">No tags</span>;
  }
  const visible = tags.slice(0, 3);
  const hidden = tags.length - visible.length;
  return (
    <div className="flex max-w-44 flex-wrap gap-1">
      {visible.map((tag) => (
        <Badge className="h-5 max-w-[5.75rem] truncate px-1.5 text-[11px] leading-none" key={tag} variant="muted">
          {tag}
        </Badge>
      ))}
      {hidden > 0 ? (
        <Badge className="h-5 px-1.5 text-[11px] leading-none" variant="outline">
          +{hidden}
        </Badge>
      ) : null}
    </div>
  );
}
