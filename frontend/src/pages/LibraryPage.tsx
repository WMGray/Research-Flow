import { BookOpen } from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { EmptyState } from "@/components/app/EmptyState";
import { ResizableSplitter } from "@/components/common/ResizableSplitter";
import { LibraryDetailPanel } from "@/components/library/LibraryDetailPanel";
import { LibraryFolderTree } from "@/components/library/LibraryFolderTree";
import { LibraryToolbar } from "@/components/library/LibraryToolbar";
import { PaperTable } from "@/components/library/PaperTable";
import { Button } from "@/components/ui/button";
import { useDialog } from "@/components/ui/DialogProvider";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  createLibraryFolder,
  createResearchLog,
  fetchPapersDashboard,
  fetchPaperContent,
  fetchResearchLogs,
  generatePaperNote,
  parsePaperPdf,
  updatePaperStar,
  updateResearchLog,
  updatePaperClassification,
  type PapersDashboardData,
  type PaperContentData,
  type PaperRecord,
  type ResearchLogRecord,
} from "@/lib/api";
import { buildLibraryFolderTree, matchesLibraryFolderNode, relativeLibraryFolderPath, type LibraryFolderTreeNode } from "@/lib/libraryFolders";
import { filterLibraryPapers, type LibraryExtraFilterId, type LibraryTabKey, type LibraryViewMode } from "@/lib/libraryWorkspace";
import { comparePapers, isReviewedLibraryPaper, type ClassificationTarget, type SortKey, type SortState } from "@/lib/libraryView";
import { useResizablePaneLayout } from "@/lib/useResizablePaneLayout";

export function LibraryPage() {
  const navigate = useNavigate();
  const params = useParams();
  const { notify } = useDialog();
  const { layout, resizeDetail, resizeTree } = useResizablePaneLayout("research-flow-library-workbench");
  const [data, setData] = useState<PapersDashboardData | null>(null);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortState>({ key: "updated", direction: "desc" });
  const [selectedNodeId, setSelectedNodeId] = useState("all");
  const [activeTab, setActiveTab] = useState<LibraryTabKey>("all");
  const [viewMode, setViewMode] = useState<LibraryViewMode>("list");
  const [extraFilters, setExtraFilters] = useState<Set<LibraryExtraFilterId>>(new Set());
  const [selectedPaperId, setSelectedPaperId] = useState(params.paperId ? decodeURIComponent(params.paperId) : "");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [starredIds, setStarredIds] = useState<Set<string>>(new Set());
  const [paperContent, setPaperContent] = useState<PaperContentData | null>(null);
  const [researchLogs, setResearchLogs] = useState<ResearchLogRecord[]>([]);
  const [createdFolderPaths, setCreatedFolderPaths] = useState<string[]>([]);
  const [folderDraft, setFolderDraft] = useState<{ parent: LibraryFolderTreeNode; level: "Domain" | "Area" | "Topic"; value: string } | null>(null);
  const [detailVisible, setDetailVisible] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const deferredQuery = useDeferredValue(query);

  const load = async () => {
    setLoading(true);
    try {
      const payload = await fetchPapersDashboard();
      setData(payload.data);
      setStarredIds(new Set(payload.data.papers.filter((paper) => paper.starred).map((paper) => paper.paper_id)));
      setError("");
      return payload.data;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "加载文库失败";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (params.paperId) {
      setSelectedPaperId(decodeURIComponent(params.paperId));
      setDetailVisible(true);
    }
  }, [params.paperId]);

  const papers = useMemo(() => (data?.papers ?? []).filter(isReviewedLibraryPaper), [data]);
  const libraryRoot = data?.paths?.library_root ?? "";
  const persistedFolderPaths = data?.folders ?? [];
  const folderTree = useMemo(
    () => buildLibraryFolderTree(papers, libraryRoot, sortedUnique([...persistedFolderPaths, ...createdFolderPaths])),
    [createdFolderPaths, libraryRoot, papers, persistedFolderPaths],
  );
  const activeNode = findFolderNode(folderTree, selectedNodeId) ?? folderTree;
  const filtered = useMemo(() => {
    const directFolderPapers = papers.filter((paper) => matchesLibraryFolderNode(paper, activeNode, libraryRoot));
    const matches = filterLibraryPapers(directFolderPapers, {
      collectionId: "all",
      query: deferredQuery,
      tab: activeTab,
      starredIds,
      extraFilters,
    });
    return matches.sort((left, right) => comparePapers(left, right, sort));
  }, [activeNode, activeTab, deferredQuery, extraFilters, libraryRoot, papers, sort, starredIds]);

  const selectedPaper = filtered.find((paper) => paper.paper_id === selectedPaperId) ?? null;

  useEffect(() => {
    if (!selectedPaper) {
      setPaperContent(null);
      setResearchLogs([]);
      return;
    }
    let cancelled = false;
    void Promise.all([fetchPaperContent(selectedPaper.paper_id), fetchResearchLogs(selectedPaper.paper_id)])
      .then(([contentPayload, logsPayload]) => {
        if (cancelled) return;
        setPaperContent(contentPayload.data);
        setResearchLogs(logsPayload.data.items);
      })
      .catch(() => {
        if (cancelled) return;
        setPaperContent(null);
        setResearchLogs([]);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPaper]);

  useEffect(() => {
    const selectedInFiltered = filtered.some((paper) => paper.paper_id === selectedPaperId);
    if (filtered.length === 0 && selectedPaperId) {
      setSelectedPaperId("");
      return;
    }
    if (filtered.length > 0 && !selectedInFiltered) {
      setSelectedPaperId(filtered[0].paper_id);
    }
  }, [filtered, selectedPaperId]);

  const selectedPapers = useMemo(() => papers.filter((paper) => selectedIds.has(paper.paper_id)), [papers, selectedIds]);

  const setSortKey = (key: SortKey) => {
    setSort((current) => ({
      key,
      direction: current.key === key && current.direction === "asc" ? "desc" : "asc",
    }));
  };

  const selectNode = (node: LibraryFolderTreeNode) => {
    setSelectedNodeId(node.id);
    setSelectedIds(new Set());
  };

  const selectPaper = (paper: PaperRecord) => {
    setSelectedPaperId(paper.paper_id);
    setDetailVisible(true);
    navigate(`/papers/${encodeURIComponent(paper.paper_id)}`);
  };

  const toggleSelection = (paperId: string) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(paperId)) {
        next.delete(paperId);
      } else {
        next.add(paperId);
      }
      return next;
    });
  };

  const toggleAll = () => {
    setSelectedIds((current) => {
      const allSelected = filtered.length > 0 && filtered.every((paper) => current.has(paper.paper_id));
      return allSelected ? new Set() : new Set(filtered.map((paper) => paper.paper_id));
    });
  };

  const toggleStar = (paperId: string) => {
    const currentPaper = papers.find((paper) => paper.paper_id === paperId);
    const nextStarred = !(currentPaper?.starred || starredIds.has(paperId));
    setStarredIds((current) => {
      const next = new Set(current);
      if (nextStarred) next.add(paperId);
      else next.delete(paperId);
      return next;
    });
    void updatePaperStar(paperId, nextStarred)
      .then(() => load())
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "更新星标失败");
        void load();
      });
  };

  const toggleExtraFilter = (filter: LibraryExtraFilterId) => {
    setExtraFilters((current) => {
      const next = new Set(current);
      if (next.has(filter)) {
        next.delete(filter);
      } else {
        next.add(filter);
      }
      return next;
    });
  };

  const createFolder = (parent: LibraryFolderTreeNode) => {
    const level = nextFolderLevel(parent);
    if (!level) {
      notify({ title: "暂不支持继续嵌套", message: "当前文库分类只支持 Domain / Area / Topic 三层。" });
      return;
    }
    setFolderDraft({ parent, level, value: "" });
  };

  const submitFolderDraft = async () => {
    if (!folderDraft) return;
    const value = folderDraft.value.trim();
    if (!value) {
      notify({ title: "名称不能为空", message: `请输入 ${folderDraft.level} 名称。` });
      return;
    }

    const nextPath = normalizeFolderPath(folderDraft.parent.path ? `${folderDraft.parent.path}/${value}` : value);
    if (findFolderNodeByPath(folderTree, nextPath) || createdFolderPaths.includes(nextPath)) {
      notify({ title: "分类已存在", message: nextPath });
      return;
    }

    try {
      const response = await createLibraryFolder(nextPath);
      const relativePath = response.data.relative_path || nextPath;
      setCreatedFolderPaths((current) => sortedUnique([...current, relativePath]));
      setSelectedNodeId(`folder:${relativePath}`);
      setFolderDraft(null);
      await load();
      notify({ title: "文件夹已创建", message: relativePath });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "创建文件夹失败";
      setError(message);
      notify({ title: "创建文件夹失败", message });
    }
  };

  const movePaperToFolder = async (paperId: string, node: LibraryFolderTreeNode) => {
    const paper = papers.find((item) => item.paper_id === paperId);
    const target = classificationTargetFromPath(node.path);
    if (!paper || !target.domain) return;

    if (samePaperClassification(paper, target)) {
      notify({ title: "分类未变化", message: `${paper.title} 已在该文件夹。` });
      return;
    }

    try {
      const response = await updatePaperClassification(paper.paper_id, target);
      const freshData = await load();
      const freshPaper = freshData?.papers.find((item) => item.paper_id === response.data.paper_id)
        ?? freshData?.papers.find((item) => item.path === response.data.path)
        ?? response.data;

      setSelectedPaperId(freshPaper.paper_id);
      setSelectedIds(new Set());
      setDetailVisible(true);
      navigate(`/papers/${encodeURIComponent(freshPaper.paper_id)}`, { replace: true });
      notify({ title: "论文已移动", message: `已移动到 ${target.domain}${target.area ? ` / ${target.area}` : ""}${target.topic ? ` / ${target.topic}` : ""}。` });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "移动论文失败";
      setError(message);
      notify({ title: "移动论文失败", message });
    }
  };

  const moveFolder = async (sourcePath: string, targetNode: LibraryFolderTreeNode) => {
    const sourceNode = findFolderNodeByPath(folderTree, sourcePath);
    const nextBasePath = movedFolderBasePath(sourcePath, targetNode.path);
    if (!sourceNode || !nextBasePath) {
      notify({ title: "暂不支持这种移动", message: "当前只支持 Area 拖到 Domain，或 Topic 拖到 Area。" });
      return;
    }

    const affectedPapers = papers.filter((paper) => matchesLibraryFolderNode(paper, sourceNode, libraryRoot));
    try {
      for (const paper of affectedPapers) {
        const currentFolderPath = relativeLibraryFolderPath(paper, libraryRoot);
        const nextFolderPath = movedPaperFolderPath(currentFolderPath, sourcePath, nextBasePath);
        await updatePaperClassification(paper.paper_id, classificationTargetFromPath(nextFolderPath));
      }

      setCreatedFolderPaths((current) => rewriteCreatedFolderPaths(current, sourcePath, nextBasePath));
      setSelectedNodeId(`folder:${nextBasePath}`);
      await load();
      notify({ title: "文件夹已移动", message: affectedPapers.length > 0 ? `已更新 ${affectedPapers.length} 篇论文。` : "空分类已在左侧树中移动。" });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "移动文件夹失败";
      setError(message);
      notify({ title: "移动文件夹失败", message });
    }
  };

  async function applyToSelected(label: string, action: (paper: PaperRecord) => Promise<unknown>) {
    const count = selectedPapers.length;
    if (count === 0) return;
    try {
      for (const paper of selectedPapers) {
        await action(paper);
      }
      setSelectedIds(new Set());
      await load();
      notify({ title: `${label}已完成`, message: `已处理 ${count} 篇论文。` });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : `${label}失败`;
      setError(message);
      notify({ title: `${label}失败`, message });
    }
  }

  async function runPaperAction(label: string, paper: PaperRecord, task: () => Promise<unknown>) {
    try {
      await task();
      const freshData = await load();
      const nextPaper = freshData?.papers.find((item) => item.paper_id === paper.paper_id)
        ?? freshData?.papers.find((item) => item.path === paper.path)
        ?? null;
      if (nextPaper) {
        setSelectedPaperId(nextPaper.paper_id);
      }
      notify({ title: `${label}已完成`, message: "文库数据已刷新。" });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : `${label}失败`;
      setError(message);
      notify({ title: `${label}失败`, message });
    }
  }

  async function createLogForPaper(paper: PaperRecord) {
    try {
      await createResearchLog(paper.paper_id, {
        title: "阅读记录",
        bullets: [],
        next_steps: [],
        tasks: [],
      });
      const payload = await fetchResearchLogs(paper.paper_id);
      setResearchLogs(payload.data.items);
      notify({ title: "研究日志已创建", message: paper.title });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "创建研究日志失败";
      setError(message);
      notify({ title: "创建研究日志失败", message });
    }
  }

  async function saveResearchLog(paper: PaperRecord, log: ResearchLogRecord) {
    try {
      await updateResearchLog(paper.paper_id, log.id, {
        title: log.title,
        bullets: log.bullets,
        next_steps: log.next_steps,
        tasks: log.tasks,
      });
      const payload = await fetchResearchLogs(paper.paper_id);
      setResearchLogs(payload.data.items);
      notify({ title: "研究日志已保存", message: log.title });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "保存研究日志失败";
      setError(message);
      notify({ title: "保存研究日志失败", message });
    }
  }

  async function openPaperPath(paper: PaperRecord, preferred: "pdf" | "folder") {
    const targetPath = preferred === "pdf" ? paper.paper_path || paper.path : paper.path || paper.paper_path;
    if (!targetPath) {
      notify({ title: "缺少路径", message: "当前论文没有可打开的本地路径。" });
      return;
    }

    if (window.researchFlow?.openPath) {
      try {
        const result = await window.researchFlow.openPath(targetPath);
        if (!result.ok) {
          await copyPathToClipboard(targetPath);
          notify({ title: "打开失败，已复制路径", message: result.error || targetPath });
        }
      } catch (err: unknown) {
        await copyPathToClipboard(targetPath);
        notify({ title: "打开失败，已复制路径", message: err instanceof Error ? err.message : targetPath });
      }
      return;
    }

    await copyPathToClipboard(targetPath);
    notify(electronBridgeMissingMessage(targetPath));
  }

  const closeDetail = () => {
    setDetailVisible(false);
    navigate("/papers", { replace: true });
  };

  return (
    <div className="flex h-screen min-w-0 overflow-hidden bg-white text-slate-900">
      <LibraryFolderTree
        libraryRoot={libraryRoot}
        selectedId={activeNode.id}
        tree={folderTree}
        width={layout.treeWidth}
        onCreateFolder={createFolder}
        onDropPaper={movePaperToFolder}
        onMoveFolder={moveFolder}
        onSelect={selectNode}
      />
      <ResizableSplitter ariaLabel="调整文件树宽度" onDrag={resizeTree} />

      <main className="flex min-w-[640px] flex-1 flex-col overflow-hidden">
        <LibraryToolbar
          activeTab={activeTab}
          extraFilters={extraFilters}
          query={query}
          selectedCount={selectedIds.size}
          viewMode={viewMode}
          onClearSelection={() => setSelectedIds(new Set())}
          onGenerateNotes={() => void applyToSelected("批量生成 Note", (paper) => generatePaperNote(paper.paper_id, false))}
          onParseSelected={() => void applyToSelected("批量解析 PDF", (paper) => parsePaperPdf(paper.paper_id, paper.parser_status === "failed"))}
          onQueryChange={setQuery}
          onTabChange={setActiveTab}
          onToggleExtraFilter={toggleExtraFilter}
          onViewModeChange={setViewMode}
        />

        {error ? <div className="border-b border-red-200 bg-red-50 px-4 py-2 text-xs text-red-700">{error}</div> : null}

        {selectedIds.size > 0 ? (
          <div className="flex h-9 items-center justify-between border-b bg-blue-50 px-4 text-xs text-blue-700">
            <span>已选择 {selectedIds.size} 篇论文</span>
            <button className="font-medium hover:underline" type="button" onClick={() => setSelectedIds(new Set())}>
              清空选择
            </button>
          </div>
        ) : null}

        <section className="min-h-0 flex-1 overflow-auto">
          {viewMode === "grid" ? (
            <GridPlaceholder papers={filtered} onSelectPaper={selectPaper} />
          ) : (
            <PaperTable
              papers={filtered}
              selectedIds={selectedIds}
              selectedPaperId={selectedPaper?.paper_id ?? ""}
              sort={sort}
              starredIds={starredIds}
              onSelectPaper={selectPaper}
              onSort={setSortKey}
              onToggleAll={toggleAll}
              onToggleSelection={toggleSelection}
              onToggleStar={toggleStar}
            />
          )}
          {!loading && filtered.length === 0 ? (
            <EmptyState className="m-4 border-0 bg-slate-50" description="当前文件夹、筛选或搜索条件下没有匹配论文。" icon={BookOpen} title="没有匹配的论文" />
          ) : null}
        </section>
      </main>

      {detailVisible ? <ResizableSplitter ariaLabel="调整详情面板宽度" onDrag={resizeDetail} /> : null}
      {detailVisible ? (
        <LibraryDetailPanel
          content={paperContent}
          paper={selectedPaper}
          researchLogs={researchLogs}
          starred={selectedPaper ? starredIds.has(selectedPaper.paper_id) : false}
          width={layout.detailWidth}
          onClose={closeDetail}
          onCreateLog={(paper) => void createLogForPaper(paper)}
          onGenerateNote={(paper) => void runPaperAction("生成 Note", paper, () => generatePaperNote(paper.paper_id, false))}
          onOpenFolder={(paper) => void openPaperPath(paper, "folder")}
          onOpenPdf={(paper) => void openPaperPath(paper, "pdf")}
          onParsePdf={(paper) => void runPaperAction(paper.parser_status === "failed" ? "重试解析" : "解析 PDF", paper, () => parsePaperPdf(paper.paper_id, paper.parser_status === "failed"))}
          onSaveLog={(paper, log) => void saveResearchLog(paper, log)}
          onToggleStar={toggleStar}
        />
      ) : null}

      <Dialog open={Boolean(folderDraft)} onOpenChange={(open) => !open && setFolderDraft(null)}>
        {folderDraft ? (
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle>新建 {folderDraft.level}</DialogTitle>
              <DialogDescription>
                父级：{folderDraft.parent.path || folderDraft.parent.label}
              </DialogDescription>
            </DialogHeader>
            <Input
              autoFocus
              placeholder={`输入 ${folderDraft.level} 名称`}
              value={folderDraft.value}
              onChange={(event) => setFolderDraft((current) => current ? { ...current, value: event.target.value } : current)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void submitFolderDraft();
                }
              }}
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => setFolderDraft(null)}>
                取消
              </Button>
              <Button onClick={() => void submitFolderDraft()}>创建</Button>
            </DialogFooter>
          </DialogContent>
        ) : null}
      </Dialog>
    </div>
  );
}

function GridPlaceholder({
  onSelectPaper,
  papers,
}: {
  papers: PaperRecord[];
  onSelectPaper: (paper: PaperRecord) => void;
}) {
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-2 p-3">
      {papers.map((paper) => (
        <button className="min-h-24 rounded-md border bg-white p-3 text-left transition-colors hover:bg-slate-50" key={paper.paper_id} type="button" onClick={() => onSelectPaper(paper)}>
          <div className="line-clamp-2 text-sm font-medium leading-5 text-slate-900">{paper.title}</div>
          <div className="mt-2 text-xs text-slate-500">{paper.venue || "未填写期刊"} {paper.year ? `· ${paper.year}` : ""}</div>
          <div className="mt-2 text-xs text-slate-500">{paper.topic || paper.area || paper.domain || "未填写方向"}</div>
        </button>
      ))}
    </div>
  );
}

function findFolderNode(node: LibraryFolderTreeNode, id: string): LibraryFolderTreeNode | null {
  if (node.id === id) return node;
  for (const child of node.children) {
    const match = findFolderNode(child, id);
    if (match) return match;
  }
  return null;
}

function findFolderNodeByPath(node: LibraryFolderTreeNode, path: string): LibraryFolderTreeNode | null {
  const normalizedPath = normalizeFolderPath(path);
  if (node.path === normalizedPath) return node;
  for (const child of node.children) {
    const match = findFolderNodeByPath(child, normalizedPath);
    if (match) return match;
  }
  return null;
}

function classificationTargetFromPath(path: string): ClassificationTarget {
  const [domain = "", area = "", topic = ""] = pathParts(path);
  return { domain, area, topic };
}

function samePaperClassification(paper: PaperRecord, target: ClassificationTarget): boolean {
  return paper.domain.trim() === target.domain && paper.area.trim() === target.area && paper.topic.trim() === target.topic;
}

function nextFolderLevel(node: LibraryFolderTreeNode): "Domain" | "Area" | "Topic" | null {
  const depth = node.kind === "all" ? 0 : pathParts(node.path).length;
  if (depth === 0) return "Domain";
  if (depth === 1) return "Area";
  if (depth === 2) return "Topic";
  return null;
}

function movedFolderBasePath(sourcePath: string, targetPath: string): string | null {
  const sourceParts = pathParts(sourcePath);
  const targetParts = pathParts(targetPath);
  if (sourceParts.length === 2 && targetParts.length === 1) {
    return normalizeFolderPath(`${targetParts[0]}/${sourceParts[1]}`);
  }
  if (sourceParts.length === 3 && targetParts.length === 2) {
    return normalizeFolderPath(`${targetParts[0]}/${targetParts[1]}/${sourceParts[2]}`);
  }
  return null;
}

function movedPaperFolderPath(currentFolderPath: string, sourcePath: string, nextBasePath: string): string {
  const sourceParts = pathParts(sourcePath);
  const suffix = pathParts(currentFolderPath).slice(sourceParts.length);
  return normalizeFolderPath([...pathParts(nextBasePath), ...suffix].slice(0, 3).join("/"));
}

function rewriteCreatedFolderPaths(paths: string[], sourcePath: string, nextBasePath: string): string[] {
  const source = normalizeFolderPath(sourcePath);
  const target = normalizeFolderPath(nextBasePath);
  return sortedUnique(
    paths.map((path) => {
      const current = normalizeFolderPath(path);
      if (current === source) return target;
      if (current.startsWith(`${source}/`)) {
        return normalizeFolderPath(`${target}/${current.slice(source.length + 1)}`);
      }
      return current;
    }),
  );
}

function normalizeFolderPath(path: string): string {
  return path.split("/").map((part) => part.trim()).filter(Boolean).join("/");
}

function pathParts(path: string): string[] {
  return normalizeFolderPath(path).split("/").filter(Boolean);
}

function sortedUnique(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort((left, right) => left.localeCompare(right));
}

async function copyPathToClipboard(path: string): Promise<void> {
  await navigator.clipboard?.writeText(path);
}

function electronBridgeMissingMessage(targetPath: string): { title: string; message: string } {
  const isElectron = window.researchFlow?.isElectron || navigator.userAgent.includes("Electron");
  if (isElectron) {
    return {
      title: "Electron 打开桥接未加载",
      message: `已复制路径到剪贴板：${targetPath}`,
    };
  }
  return {
    title: "已复制论文路径",
    message: "当前 Web 环境不能直接打开本地路径，路径已复制到剪贴板。",
  };
}
