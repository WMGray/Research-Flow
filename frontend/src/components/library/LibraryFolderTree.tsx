import { BookOpen, ChevronDown, ChevronRight, Folder, FolderOpen, FolderPlus } from "lucide-react";
import { type DragEvent, type MouseEvent, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { LibraryFolderTreeNode } from "@/lib/libraryFolders";
import { cn } from "@/lib/utils";

type LibraryFolderTreeProps = {
  tree: LibraryFolderTreeNode;
  selectedId: string;
  width: number;
  libraryRoot?: string;
  onCreateFolder?: (node: LibraryFolderTreeNode) => void;
  onDropPaper?: (paperId: string, node: LibraryFolderTreeNode) => Promise<void> | void;
  onMoveFolder?: (sourcePath: string, node: LibraryFolderTreeNode) => Promise<void> | void;
  onSelect: (node: LibraryFolderTreeNode) => void;
};

const PAPER_DRAG_TYPE = "application/x-research-flow-paper-id";
const FOLDER_DRAG_TYPE = "application/x-research-flow-folder-path";

type ContextMenuState = {
  node: LibraryFolderTreeNode;
  x: number;
  y: number;
};

export function LibraryFolderTree({ libraryRoot, onCreateFolder, onDropPaper, onMoveFolder, onSelect, selectedId, tree, width }: LibraryFolderTreeProps) {
  const defaultOpenIds = useMemo(() => new Set(["all", ...tree.children.slice(0, 5).map((node) => node.id)]), [tree]);
  const [openIds, setOpenIds] = useState<Set<string>>(defaultOpenIds);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [dragOverId, setDragOverId] = useState("");

  useEffect(() => {
    setOpenIds((current) => new Set([...current, ...defaultOpenIds]));
  }, [defaultOpenIds]);

  useEffect(() => {
    setOpenIds((current) => new Set([...current, ...ancestorIdsFor(tree, selectedId)]));
  }, [selectedId, tree]);

  useEffect(() => {
    if (!contextMenu) return undefined;

    const close = () => setContextMenu(null);
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        close();
      }
    };

    window.addEventListener("click", close);
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [contextMenu]);

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

  const openContextMenu = (event: MouseEvent, node: LibraryFolderTreeNode) => {
    if (!onCreateFolder) return;
    event.preventDefault();
    onSelect(node);
    setContextMenu({ node, x: event.clientX, y: event.clientY });
  };

  return (
    <aside className="hidden shrink-0 border-r bg-card/70 xl:block" style={{ width }}>
      <div className="border-b px-3 py-3">
        <div className="text-sm font-semibold">{tree.label}</div>
        <div className="mt-1 truncate text-xs text-muted-foreground" title={libraryRoot}>
          {libraryRoot || "按真实文件夹路径管理"}
        </div>
      </div>
      <ScrollArea className="h-[calc(100vh-7.25rem)]">
        <div className="p-2">
          <TreeNodeRow
            depth={0}
            dragOverId={dragOverId}
            node={tree}
            openIds={openIds}
            selectedId={selectedId}
            onContextMenu={openContextMenu}
            onDragLeave={() => setDragOverId("")}
            onDragOver={setDragOverId}
            onDropPaper={onDropPaper}
            onMoveFolder={onMoveFolder}
            onSelect={onSelect}
            onToggle={toggle}
          />
        </div>
      </ScrollArea>
      {contextMenu ? (
        <FolderContextMenu
          node={contextMenu.node}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
          onCreate={() => {
            onCreateFolder?.(contextMenu.node);
            setContextMenu(null);
          }}
        />
      ) : null}
    </aside>
  );
}

function TreeNodeRow({
  depth,
  dragOverId,
  node,
  onContextMenu,
  onDragLeave,
  onDragOver,
  onDropPaper,
  onMoveFolder,
  onSelect,
  onToggle,
  openIds,
  selectedId,
}: {
  depth: number;
  dragOverId: string;
  node: LibraryFolderTreeNode;
  openIds: Set<string>;
  selectedId: string;
  onContextMenu: (event: MouseEvent, node: LibraryFolderTreeNode) => void;
  onDragLeave: () => void;
  onDragOver: (id: string) => void;
  onDropPaper?: (paperId: string, node: LibraryFolderTreeNode) => Promise<void> | void;
  onMoveFolder?: (sourcePath: string, node: LibraryFolderTreeNode) => Promise<void> | void;
  onSelect: (node: LibraryFolderTreeNode) => void;
  onToggle: (id: string) => void;
}) {
  const expanded = openIds.has(node.id);
  const selected = selectedId === node.id;
  const hasChildren = node.children.length > 0;
  const Icon = iconForNode(node, expanded);
  const acceptsDrop = node.kind === "folder";

  const handleDragOver = (event: DragEvent) => {
    if (!acceptsDrop || (!hasPaperDragPayload(event) && !hasFolderDragPayload(event))) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    onDragOver(node.id);
  };

  const handleDragStart = (event: DragEvent) => {
    if (node.kind !== "folder") return;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData(FOLDER_DRAG_TYPE, node.path);
  };

  const handleDrop = (event: DragEvent) => {
    if (!acceptsDrop) return;
    const paperId = event.dataTransfer.getData(PAPER_DRAG_TYPE) || event.dataTransfer.getData("text/plain");
    const folderPath = event.dataTransfer.getData(FOLDER_DRAG_TYPE);
    if (!paperId && !folderPath) return;

    event.preventDefault();
    onDragLeave();
    if (paperId) {
      void onDropPaper?.(paperId, node);
      return;
    }
    if (folderPath && folderPath !== node.path) {
      void onMoveFolder?.(folderPath, node);
    }
  };

  return (
    <div>
      <div
        className={cn(
          "group flex h-8 items-center gap-1 rounded-md px-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
          selected && "bg-muted text-foreground",
          dragOverId === node.id && "bg-primary/10 text-foreground ring-1 ring-primary/40",
        )}
        draggable={node.kind === "folder"}
        style={{ paddingLeft: `${depth * 12 + 6}px` }}
        onContextMenu={(event) => onContextMenu(event, node)}
        onDragLeave={onDragLeave}
        onDragOver={handleDragOver}
        onDragStart={handleDragStart}
        onDrop={handleDrop}
      >
        <Button className="h-5 w-5" size="icon" variant="ghost" disabled={!hasChildren} onClick={() => onToggle(node.id)}>
          {hasChildren ? expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" /> : <span className="h-3.5 w-3.5" />}
        </Button>
        <button className="flex min-w-0 flex-1 items-center gap-2 text-left" title={node.path || node.label} type="button" onClick={() => onSelect(node)}>
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
            <TreeNodeRow
              depth={depth + 1}
              dragOverId={dragOverId}
              key={child.id}
              node={child}
              openIds={openIds}
              selectedId={selectedId}
              onContextMenu={onContextMenu}
              onDragLeave={onDragLeave}
              onDragOver={onDragOver}
              onDropPaper={onDropPaper}
              onMoveFolder={onMoveFolder}
              onSelect={onSelect}
              onToggle={onToggle}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function iconForNode(node: LibraryFolderTreeNode, expanded: boolean) {
  if (node.kind === "all") return BookOpen;
  return expanded ? FolderOpen : Folder;
}

function FolderContextMenu({
  node,
  onClose,
  onCreate,
  x,
  y,
}: {
  node: LibraryFolderTreeNode;
  x: number;
  y: number;
  onClose: () => void;
  onCreate: () => void;
}) {
  const level = nextFolderLevel(node);

  return (
    <div
      className="fixed z-50 min-w-44 rounded-md border bg-popover p-1 text-sm text-popover-foreground shadow-md"
      style={{ left: x, top: y }}
      onClick={(event) => event.stopPropagation()}
    >
      {level ? (
        <button className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left outline-none hover:bg-accent focus:bg-accent" type="button" onClick={onCreate}>
          <FolderPlus className="h-4 w-4" />
          新建 {level}
        </button>
      ) : (
        <div className="px-2 py-1.5 text-xs text-muted-foreground">Topic 下不再嵌套</div>
      )}
      <button className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left outline-none hover:bg-accent focus:bg-accent" type="button" onClick={onClose}>
        取消
      </button>
    </div>
  );
}

function nextFolderLevel(node: LibraryFolderTreeNode): "Domain" | "Area" | "Topic" | null {
  const depth = node.kind === "all" ? 0 : node.path.split("/").filter(Boolean).length;
  if (depth === 0) return "Domain";
  if (depth === 1) return "Area";
  if (depth === 2) return "Topic";
  return null;
}

function ancestorIdsFor(root: LibraryFolderTreeNode, selectedId: string): string[] {
  const path: string[] = [];
  if (collectAncestorIds(root, selectedId, path)) {
    return path;
  }
  return [];
}

function collectAncestorIds(node: LibraryFolderTreeNode, selectedId: string, path: string[]): boolean {
  if (node.id === selectedId) {
    return true;
  }

  for (const child of node.children) {
    path.push(node.id);
    if (collectAncestorIds(child, selectedId, path)) {
      return true;
    }
    path.pop();
  }
  return false;
}

function hasPaperDragPayload(event: DragEvent): boolean {
  return Array.from(event.dataTransfer.types).includes(PAPER_DRAG_TYPE);
}

function hasFolderDragPayload(event: DragEvent): boolean {
  return Array.from(event.dataTransfer.types).includes(FOLDER_DRAG_TYPE);
}
