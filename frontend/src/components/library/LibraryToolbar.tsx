import { Download, LayoutGrid, List, MoreHorizontal, Search } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import type { LibraryExtraFilterId, LibraryTabKey, LibraryViewMode } from "@/lib/libraryWorkspace";
import { cn } from "@/lib/utils";

type LibraryToolbarProps = {
  query: string;
  activeTab: LibraryTabKey;
  viewMode: LibraryViewMode;
  selectedCount: number;
  extraFilters: Set<LibraryExtraFilterId>;
  onQueryChange: (value: string) => void;
  onTabChange: (tab: LibraryTabKey) => void;
  onViewModeChange: (mode: LibraryViewMode) => void;
  onToggleExtraFilter: (filter: LibraryExtraFilterId) => void;
  onParseSelected: () => void;
  onGenerateNotes: () => void;
  onClearSelection: () => void;
};

const tabs: Array<{ id: LibraryTabKey; label: string }> = [
  { id: "all", label: "全部" },
  { id: "needs_pdf", label: "需要 PDF" },
  { id: "pending_refine", label: "待处理精读" },
  { id: "reading_queue", label: "阅读中" },
  { id: "reviewed", label: "已评审" },
  { id: "more", label: "更多筛选" },
];

const extraFilterLabels: Record<LibraryExtraFilterId, string> = {
  starred: "只看星标",
  has_notes: "已有笔记",
  no_tags: "未分类标签",
  updated_7d: "本周更新",
  updated_30d: "近30天导入",
};

export function LibraryToolbar({
  activeTab,
  extraFilters,
  onClearSelection,
  onGenerateNotes,
  onParseSelected,
  onQueryChange,
  onTabChange,
  onToggleExtraFilter,
  onViewModeChange,
  query,
  selectedCount,
  viewMode,
}: LibraryToolbarProps) {
  return (
    <header className="border-b bg-white px-4 py-3">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="text-xs text-slate-500">Research-Flow &gt; Papers &gt; 01_Papers</div>
          <h1 className="mt-1 text-xl font-semibold text-slate-900">文库</h1>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button asChild className="h-8" size="sm">
            <Link to="/discover">
              <Download className="h-3.5 w-3.5" />
              导入论文
            </Link>
          </Button>
          <div className="flex rounded-md border bg-slate-50 p-0.5">
            <Button
              aria-label="列表视图"
              className={cn("h-7 w-7 rounded-sm", viewMode === "list" && "bg-white shadow-sm")}
              size="icon"
              variant="ghost"
              onClick={() => onViewModeChange("list")}
            >
              <List className="h-3.5 w-3.5" />
            </Button>
            <Button
              aria-label="网格视图"
              className={cn("h-7 w-7 rounded-sm", viewMode === "grid" && "bg-white shadow-sm")}
              size="icon"
              variant="ghost"
              onClick={() => onViewModeChange("grid")}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </Button>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button aria-label="更多操作" className="h-8 w-8" size="icon" variant="outline">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>批量操作</DropdownMenuLabel>
              <DropdownMenuItem disabled={selectedCount === 0} onSelect={onParseSelected}>
                解析选中 PDF
              </DropdownMenuItem>
              <DropdownMenuItem disabled={selectedCount === 0} onSelect={onGenerateNotes}>
                生成选中 Note
              </DropdownMenuItem>
              <DropdownMenuItem disabled={selectedCount === 0} onSelect={onClearSelection}>
                清空选择
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuLabel>更多筛选</DropdownMenuLabel>
              {(Object.keys(extraFilterLabels) as LibraryExtraFilterId[]).map((filter) => (
                <DropdownMenuCheckboxItem
                  checked={extraFilters.has(filter)}
                  key={filter}
                  onCheckedChange={() => onToggleExtraFilter(filter)}
                >
                  {extraFilterLabels[filter]}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <div className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <Input
            aria-label="搜索文库"
            className="h-8 rounded-md border-slate-200 bg-slate-50 pl-8 text-xs"
            placeholder="标题、作者、关键词、标签、DOI..."
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {tabs.map((tab) => (
          <button
            className={cn(
              "h-7 rounded-md border border-transparent px-2.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100",
              activeTab === tab.id && "border-blue-100 bg-blue-50 text-blue-700",
            )}
            key={tab.id}
            type="button"
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </header>
  );
}
