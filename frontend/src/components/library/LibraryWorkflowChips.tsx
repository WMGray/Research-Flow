import { Badge } from "@/components/ui/badge";
import type { PaperRecord } from "@/lib/api";
import { buildDetailWorkflow, type DetailWorkflowItem } from "@/components/library/paperDetailData";
import { cn } from "@/lib/utils";

type LibraryWorkflowChipsProps = {
  paper: PaperRecord;
  maxVisible?: number;
  className?: string;
  onChipClick?: (item: DetailWorkflowItem) => void;
};

export function LibraryWorkflowChips({ className, maxVisible, onChipClick, paper }: LibraryWorkflowChipsProps) {
  const items = buildDetailWorkflow(paper);
  const visible = typeof maxVisible === "number" ? items.slice(0, maxVisible) : items;
  const hidden = typeof maxVisible === "number" ? Math.max(items.length - visible.length, 0) : 0;

  return (
    <div className={cn("flex min-w-0 flex-wrap items-center gap-1", className)}>
      {visible.map((item) => {
        const chip = (
          <Badge
            className={cn(
              "h-5 max-w-[7.5rem] truncate px-1.5 text-[11px] leading-none",
              onChipClick && "cursor-pointer hover:brightness-95",
            )}
            title={`${item.label}: ${item.status}`}
            variant={item.tone}
          >
            {item.status}
          </Badge>
        );

        if (!onChipClick) {
          return <span key={`${item.key}-${item.status}`}>{chip}</span>;
        }

        return (
          <button key={`${item.key}-${item.status}`} type="button" onClick={() => onChipClick(item)}>
            {chip}
          </button>
        );
      })}
      {hidden > 0 ? (
        <Badge className="h-5 px-1.5 text-[11px] leading-none" variant="outline">
          +{hidden}
        </Badge>
      ) : null}
    </div>
  );
}
