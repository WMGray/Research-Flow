import { ChevronDown, ChevronRight, Folder, FolderOpen } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ClassificationTreeNode } from "@/lib/libraryView";
import { cn } from "@/lib/utils";

type DomainTreeProps = {
  tree: ClassificationTreeNode;
  selectedId: string;
  onSelect: (node: ClassificationTreeNode) => void;
};

export function DomainTree({ onSelect, selectedId, tree }: DomainTreeProps) {
  const initialOpen = useMemo(() => new Set(["all", ...tree.children.slice(0, 4).map((node) => node.id)]), [tree]);
  const [openIds, setOpenIds] = useState<Set<string>>(initialOpen);

  const toggle = (id: string) => {
    setOpenIds((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <aside className="hidden w-64 shrink-0 border-r bg-card/60 xl:block">
      <div className="border-b px-3 py-3">
        <div className="text-sm font-semibold">Domain</div>
        <div className="mt-1 text-xs text-muted-foreground">按领域、Area 与 Topic 管理论文</div>
      </div>
      <ScrollArea className="h-[calc(100vh-7.25rem)]">
        <div className="p-2">
          <TreeNodeRow depth={0} node={tree} openIds={openIds} selectedId={selectedId} onSelect={onSelect} onToggle={toggle} />
        </div>
      </ScrollArea>
    </aside>
  );
}

function TreeNodeRow({
  depth,
  node,
  onSelect,
  onToggle,
  openIds,
  selectedId,
}: {
  depth: number;
  node: ClassificationTreeNode;
  openIds: Set<string>;
  selectedId: string;
  onSelect: (node: ClassificationTreeNode) => void;
  onToggle: (id: string) => void;
}) {
  const expanded = openIds.has(node.id);
  const selected = selectedId === node.id;
  const hasChildren = node.children.length > 0;
  const Icon = expanded ? FolderOpen : Folder;

  return (
    <div>
      <div
        className={cn(
          "group flex h-8 items-center gap-1 rounded-md px-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
          selected && "bg-muted text-foreground",
        )}
        style={{ paddingLeft: `${depth * 12 + 6}px` }}
      >
        <Button className="h-5 w-5" size="icon" variant="ghost" disabled={!hasChildren} onClick={() => onToggle(node.id)}>
          {hasChildren ? expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" /> : <span className="h-3.5 w-3.5" />}
        </Button>
        <button className="flex min-w-0 flex-1 items-center gap-2 text-left" type="button" onClick={() => onSelect(node)}>
          <Icon className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{node.label}</span>
        </button>
        <Badge className="px-1.5 py-0 text-[11px]" variant={selected ? "secondary" : "muted"}>
          {node.count}
        </Badge>
      </div>
      {expanded && hasChildren ? (
        <div>
          {node.children.map((child) => (
            <TreeNodeRow depth={depth + 1} key={child.id} node={child} openIds={openIds} selectedId={selectedId} onSelect={onSelect} onToggle={onToggle} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
