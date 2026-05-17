import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { SortDirection } from "@/lib/libraryView";
import { cn } from "@/lib/utils";

type SortableHeaderProps<T extends string> = {
  label: string;
  sortKey: T;
  activeKey: T;
  direction: SortDirection;
  className?: string;
  onSort: (key: T) => void;
};

export function SortableHeader<T extends string>({
  activeKey,
  className,
  direction,
  label,
  onSort,
  sortKey,
}: SortableHeaderProps<T>) {
  const active = activeKey === sortKey;
  const Icon = active ? (direction === "asc" ? ArrowUp : ArrowDown) : ChevronsUpDown;

  return (
    <Button className={cn("-ml-2 h-7 px-2 text-xs uppercase text-muted-foreground", className)} size="sm" variant="ghost" onClick={() => onSort(sortKey)}>
      {label}
      <Icon className={cn("h-3.5 w-3.5", !active && "opacity-45")} />
    </Button>
  );
}
