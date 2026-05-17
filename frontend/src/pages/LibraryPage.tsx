import { Archive, BookOpen, ChevronRight, FileText, FolderPen, Sparkles, Tag, Trash2 } from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { EmptyState } from "@/components/app/EmptyState";
import { FilterSearch } from "@/components/app/FilterSearch";
import { PageShell } from "@/components/app/PageShell";
import { BatchActionBar, type BatchAction } from "@/components/common/BatchActionBar";
import { ResizableSplitter } from "@/components/common/ResizableSplitter";
import { LibraryFolderTree } from "@/components/library/LibraryFolderTree";
import { PaperTable } from "@/components/library/PaperTable";
import { ResponsivePaperInspector } from "@/components/papers/ResponsivePaperInspector";
import type { EditableMetadataValue } from "@/components/papers/PaperDetailPanel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useDialog } from "@/components/ui/DialogProvider";
import {
  fetchLibraryDashboard,
  generatePaperNote,
  parsePaperPdf,
  rejectPaper,
  updatePaperClassification,
  type LibraryDashboardData,
  type PaperRecord,
} from "@/lib/api";
import { buildLibraryFolderTree, matchesLibraryFolderNode, relativeLibraryFolderPath, type LibraryFolderTreeNode } from "@/lib/libraryFolders";
import {
  buildClassificationOptions,
  comparePapers,
  filterPapersByQuery,
  isReviewedLibraryPaper,
  type ClassificationTarget,
  type SortKey,
  type SortState,
} from "@/lib/libraryView";
import { useResizablePaneLayout } from "@/lib/useResizablePaneLayout";

export function LibraryPage() {
  const navigate = useNavigate();
  const params = useParams();
  const { confirm, notify } = useDialog();
  const { layout, resizeDetail, resizeTree } = useResizablePaneLayout("research-flow-library-panes");
  const [data, setData] = useState<LibraryDashboardData | null>(null);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortState>({ key: "updated", direction: "desc" });
  const [selectedNodeId, setSelectedNodeId] = useState("all");
  const [selectedPaperId, setSelectedPaperId] = useState(params.paperId ? decodeURIComponent(params.paperId) : "");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [createdFolderPaths, setCreatedFolderPaths] = useState<string[]>([]);
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const deferredQuery = useDeferredValue(query);

  const load = async () => {
    setLoading(true);
    try {
      const payload = await fetchLibraryDashboard();
      setData(payload.data);
      setError("");
      return payload.data;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "加载文库失败");
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
      setInspectorCollapsed(false);
    }
  }, [params.paperId]);

  const papers = useMemo(() => (data?.papers ?? []).filter(isReviewedLibraryPaper), [data]);
  const libraryRoot = data?.paths?.library_root ?? "";
  const tree = useMemo(() => buildLibraryFolderTree(papers, libraryRoot, createdFolderPaths), [createdFolderPaths, libraryRoot, papers]);
  const activeNode = findNode(tree, selectedNodeId) ?? tree;
  const classificationOptions = useMemo(() => buildClassificationOptions(papers), [papers]);
  const filtered = useMemo(() => {
    const byNode = papers.filter((paper) => matchesLibraryFolderNode(paper, activeNode, libraryRoot));
    return filterPapersByQuery(byNode, deferredQuery).sort((left, right) => comparePapers(left, right, sort));
  }, [activeNode, deferredQuery, libraryRoot, papers, sort]);

  const selectedPaper = filtered.find((paper) => paper.paper_id === selectedPaperId)
    ?? papers.find((paper) => paper.paper_id === selectedPaperId)
    ?? null;

  useEffect(() => {
    if (selectedPaper && selectedPaper.paper_id !== selectedPaperId) {
      setSelectedPaperId(selectedPaper.paper_id);
    }
    if (!selectedPaper && selectedPaperId) {
      setSelectedPaperId("");
    }
  }, [selectedPaper, selectedPaperId]);

  const selectedPapers = useMemo(() => papers.filter((paper) => selectedIds.has(paper.paper_id)), [papers, selectedIds]);

  const setSortKey = (key: SortKey) => {
    setSort((current) => ({
      key,
      direction: current.key === key && current.direction === "asc" ? "desc" : "asc",
    }));
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

  const clearFilters = () => {
    setQuery("");
    setSelectedIds(new Set());
  };

  const createFolder = (parent: LibraryFolderTreeNode) => {
    const level = nextFolderLevel(parent);
    if (!level) {
      notify({ title: "暂不支持继续嵌套", message: "当前文库分类只持久化 Domain / Area / Topic 三层。" });
      return;
    }

    const value = window.prompt(`新建 ${level}`);
    if (!value?.trim()) return;
    const cleanValue = value.trim();
    const nextPath = normalizeFolderPath(parent.path ? `${parent.path}/${cleanValue}` : cleanValue);

    if (findNodeByPath(tree, nextPath) || createdFolderPaths.includes(nextPath)) {
      notify({ title: "分类已存在", message: nextPath });
      return;
    }

    setCreatedFolderPaths((current) => sortedUnique([...current, nextPath]));
    setSelectedNodeId(`folder:${nextPath}`);
    notify({ title: `${level} 已新增`, message: "拖入论文后会写入后端并移动到该分类。" });
  };

  const movePaperToFolder = async (paperId: string, node: LibraryFolderTreeNode) => {
    const paper = papers.find((item) => item.paper_id === paperId);
    const target = classificationTargetFromFolder(node);
    if (!paper || !target.domain) {
      return;
    }

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

      if (paper.paper_id === selectedPaperId) {
        setSelectedPaperId(freshPaper.paper_id);
        navigate(`/library/${encodeURIComponent(freshPaper.paper_id)}`, { replace: true });
      }
      setSelectedIds(new Set());
      notify({ title: "论文已移动", message: `已移动到 ${target.domain}${target.area ? ` / ${target.area}` : ""}${target.topic ? ` / ${target.topic}` : ""}。` });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "移动论文失败";
      setError(message);
      notify({ title: "移动论文失败", message });
    }
  };

  const moveFolder = async (sourcePath: string, targetNode: LibraryFolderTreeNode) => {
    const sourceNode = findNodeByPath(tree, sourcePath);
    const targetPath = normalizeFolderPath(targetNode.path);
    const nextBasePath = movedFolderBasePath(sourcePath, targetPath);
    if (!sourceNode || !nextBasePath) {
      notify({ title: "暂不支持这种移动", message: "当前只支持 Area 拖到 Domain，或 Topic 拖到 Area。" });
      return;
    }
    if (normalizeFolderPath(sourcePath) === nextBasePath) {
      notify({ title: "文件夹未变化", message: sourcePath });
      return;
    }

    const affectedPapers = papers.filter((paper) => matchesLibraryFolderNode(paper, sourceNode, libraryRoot));
    if (affectedPapers.length > 0) {
      const accepted = await confirm({
        title: "移动文件夹？",
        message: `将更新 ${affectedPapers.length} 篇论文的分类，并由后端移动对应论文目录。`,
        confirmLabel: "移动",
        cancelLabel: "取消",
      });
      if (!accepted) return;
    }

    try {
      for (const paper of affectedPapers) {
        const currentFolderPath = relativeLibraryFolderPath(paper, libraryRoot);
        const nextFolderPath = movedPaperFolderPath(currentFolderPath, sourcePath, nextBasePath);
        await updatePaperClassification(paper.paper_id, classificationTargetFromPath(nextFolderPath));
      }

      setCreatedFolderPaths((current) => rewriteCreatedFolderPaths(current, sourcePath, nextBasePath));
      setSelectedNodeId(`folder:${nextBasePath}`);
      await load();
      notify({
        title: "文件夹已移动",
        message: affectedPapers.length > 0 ? `已更新 ${affectedPapers.length} 篇论文。` : "空分类已在左侧树中移动；拖入论文后会持久化。",
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "移动文件夹失败";
      setError(message);
      notify({ title: "移动文件夹失败", message });
    }
  };

  const applyToSelected = async (label: string, action: (paper: PaperRecord) => Promise<unknown>) => {
    const count = selectedPapers.length;
    for (const paper of selectedPapers) {
      await action(paper);
    }
    setSelectedIds(new Set());
    await load();
    notify({ title: `${label}已完成`, message: `已处理 ${count} 篇论文。` });
  };

  const batchActions: BatchAction[] = [
    {
      id: "domain",
      label: "批量设置 Domain",
      icon: <FolderPen className="h-3.5 w-3.5" />,
      onClick: () => void batchSetClassification("Domain", { domain: "Representation Learning", area: "", topic: "" }),
    },
    {
      id: "area",
      label: "批量设置 Area",
      onClick: () => void batchSetClassification("Area", { domain: selectedPapers[0]?.domain || "Representation Learning", area: "General", topic: selectedPapers[0]?.topic || "" }),
    },
    {
      id: "topic",
      label: "批量设置 Topic",
      onClick: () => void batchSetClassification("Topic", { domain: selectedPapers[0]?.domain || "Representation Learning", area: selectedPapers[0]?.area || "General", topic: "Representation Learning" }),
    },
    {
      id: "tags",
      label: "批量添加 Tags",
      icon: <Tag className="h-3.5 w-3.5" />,
      disabledReason: "后端尚未提供批量 Tags 持久化接口。",
      onClick: () => undefined,
    },
    {
      id: "parse",
      label: "批量解析 PDF",
      icon: <FileText className="h-3.5 w-3.5" />,
      onClick: () => void applyToSelected("批量解析", (paper) => parsePaperPdf(paper.paper_id, paper.parser_status === "failed")),
    },
    {
      id: "note",
      label: "批量生成 Note",
      icon: <Sparkles className="h-3.5 w-3.5" />,
      onClick: () => void applyToSelected("批量生成 Note", (paper) => generatePaperNote(paper.paper_id, false)),
    },
    {
      id: "archive",
      label: "批量归档",
      icon: <Archive className="h-3.5 w-3.5" />,
      onClick: () => void confirmDanger("批量归档论文", "将按当前后端 reject/archive 策略处理选中的论文。", () => applyToSelected("批量归档", (paper) => rejectPaper(paper.paper_id))),
    },
    {
      id: "delete",
      label: "批量删除",
      icon: <Trash2 className="h-3.5 w-3.5" />,
      variant: "destructive",
      onClick: () => void confirmDanger("批量删除论文", "删除是高风险操作，将按当前后端策略执行。", () => applyToSelected("批量删除", (paper) => rejectPaper(paper.paper_id))),
    },
  ];

  async function batchSetClassification(label: string, target: ClassificationTarget) {
    await applyToSelected(`批量设置 ${label}`, (paper) =>
      updatePaperClassification(paper.paper_id, {
        domain: target.domain || paper.domain,
        area: target.area || paper.area,
        topic: target.topic || paper.topic,
      }),
    );
  }

  async function confirmDanger(title: string, message: string, task: () => Promise<void>) {
    const accepted = await confirm({ title, message, confirmLabel: "确认", cancelLabel: "取消", danger: true });
    if (accepted) {
      await task();
    }
  }

  async function saveMetadata(value: EditableMetadataValue) {
    if (!selectedPaper) return;
    const response = await updatePaperClassification(selectedPaper.paper_id, {
      domain: value.domain,
      area: value.area,
      topic: value.topic,
      title: value.title,
      venue: value.venue,
      year: value.year.trim() ? Number(value.year) : null,
      tags: splitTags(value.tags),
      status: value.status,
      paper_path: value.paper_path,
      note_path: value.note_path,
      refined_path: value.refined_path,
    });
    const freshData = await load();
    const freshPaper = freshData?.papers.find((paper) => paper.paper_id === response.data.paper_id)
      ?? freshData?.papers.find((paper) => paper.path === response.data.path)
      ?? response.data;
    setSelectedPaperId(freshPaper.paper_id);
    setInspectorCollapsed(false);
    navigate(`/library/${encodeURIComponent(freshPaper.paper_id)}`, { replace: true });
    notify({
      title: "Metadata 已保存",
      message: "标题、venue、year、tags、状态和分类信息已写入后端并刷新当前论文。",
    });
  }

  async function openFolder(paper: PaperRecord) {
    const targetPath = paper.path || paper.paper_path;
    if (!targetPath) {
      notify({ title: "缺少路径", message: "当前论文没有可打开的本地路径。" });
      return;
    }

    if (window.researchFlow?.openPath) {
      try {
        const result = await window.researchFlow.openPath(targetPath);
        if (!result.ok) {
          await copyPathToClipboard(targetPath);
          notify({ title: "打开文件夹失败，已复制路径", message: result.error || targetPath });
        }
      } catch (err: unknown) {
        await copyPathToClipboard(targetPath);
        notify({ title: "打开文件夹失败，已复制路径", message: err instanceof Error ? err.message : targetPath });
      }
      return;
    }

    await copyPathToClipboard(targetPath);
    notify(electronBridgeMissingMessage(targetPath));
  }

  async function runPaperAction(label: string, task: () => Promise<unknown>) {
    try {
      await task();
      const freshData = await load();
      const nextPaper = freshData?.papers.find((paper) => paper.paper_id === selectedPaperId)
        ?? freshData?.papers.find((paper) => paper.path === selectedPaper?.path)
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

  const selectNode = (node: LibraryFolderTreeNode) => {
    setSelectedNodeId(node.id);
    setSelectedIds(new Set());
  };

  const selectPaper = (paper: PaperRecord) => {
    setSelectedPaperId(paper.paper_id);
    setInspectorCollapsed(false);
    navigate(`/library/${encodeURIComponent(paper.paper_id)}`);
  };

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] min-w-0 overflow-hidden">
      <LibraryFolderTree
        libraryRoot={libraryRoot}
        selectedId={activeNode.id}
        tree={tree}
        width={layout.treeWidth}
        onCreateFolder={createFolder}
        onDropPaper={movePaperToFolder}
        onMoveFolder={moveFolder}
        onSelect={selectNode}
      />
      <ResizableSplitter ariaLabel="调整 Papers 树宽度" onDrag={resizeTree} />

      <PageShell
        actions={
          <>
            <Button asChild size="sm" variant="outline">
              <Link to="/discover">
                发现论文
                <ChevronRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button size="sm" variant="outline" onClick={() => navigate("/uncategorized")}>
              处理未分类
            </Button>
          </>
        }
        className="min-w-[520px] flex-1"
        description="按真实 Papers 文件夹路径浏览文库，三栏布局可拖拽调整，打开详情后列表自动缩放。"
        title="文库"
      >
        {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

        <section className="flex flex-col gap-3 rounded-lg border bg-card p-3 xl:flex-row xl:items-center">
          <FilterSearch className="min-w-0 flex-1" label="搜索文库" placeholder="标题、venue、年份、路径、标签..." value={query} onChange={setQuery} />
          <Button size="sm" variant="outline" onClick={clearFilters}>
            清空
          </Button>
        </section>

        <BatchActionBar actions={batchActions} count={selectedIds.size} onClear={() => setSelectedIds(new Set())} />

        <Card className="min-w-0 overflow-hidden">
          <span className="sr-only">Title Venue Year Tags Status Updated</span>
          <PaperTable
            papers={filtered}
            selectedIds={selectedIds}
            selectedPaperId={selectedPaper?.paper_id ?? ""}
            sort={sort}
            onSelectPaper={selectPaper}
            onSort={setSortKey}
            onToggleAll={toggleAll}
            onToggleSelection={toggleSelection}
          />
          {!loading && filtered.length === 0 ? (
            <EmptyState className="m-4 border-0 bg-muted/40" description="当前文件夹或搜索条件下没有论文。" icon={BookOpen} title="没有匹配的论文" />
          ) : null}
        </Card>
      </PageShell>

      {!inspectorCollapsed ? <ResizableSplitter ariaLabel="调整详情栏宽度" onDrag={resizeDetail} /> : null}
      <ResponsivePaperInspector
        collapsed={inspectorCollapsed}
        paper={selectedPaper}
        width={layout.detailWidth}
        onGenerateNote={(paper) => runPaperAction("生成 Note", () => generatePaperNote(paper.paper_id, false))}
        classificationOptions={classificationOptions}
        onMetadataSave={saveMetadata}
        onOpenFolder={openFolder}
        onParsePdf={(paper) => runPaperAction(paper.parser_status === "failed" ? "重试解析" : "解析 PDF", () => parsePaperPdf(paper.paper_id, paper.parser_status === "failed"))}
        onToggleCollapsed={() => setInspectorCollapsed((value) => !value)}
      />
    </div>
  );
}

function findNode(node: LibraryFolderTreeNode, id: string): LibraryFolderTreeNode | null {
  if (node.id === id) {
    return node;
  }
  for (const child of node.children) {
    const match = findNode(child, id);
    if (match) {
      return match;
    }
  }
  return null;
}

function classificationTargetFromFolder(node: LibraryFolderTreeNode): ClassificationTarget {
  return classificationTargetFromPath(node.path);
}

function classificationTargetFromPath(path: string): ClassificationTarget {
  const [domain = "", area = "", topic = ""] = pathParts(path);
  return normalizeTarget({ domain, area, topic });
}

function samePaperClassification(paper: PaperRecord, target: ClassificationTarget): boolean {
  return paper.domain.trim() === target.domain && paper.area.trim() === target.area && paper.topic.trim() === target.topic;
}

function nextFolderLevel(node: LibraryFolderTreeNode): "Domain" | "Area" | "Topic" | null {
  const depth = node.kind === "all" ? 0 : node.path.split("/").filter(Boolean).length;
  if (depth === 0) return "Domain";
  if (depth === 1) return "Area";
  if (depth === 2) return "Topic";
  return null;
}

function findNodeByPath(node: LibraryFolderTreeNode, path: string): LibraryFolderTreeNode | null {
  if (node.path === path) {
    return node;
  }
  for (const child of node.children) {
    const match = findNodeByPath(child, path);
    if (match) {
      return match;
    }
  }
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

function normalizeTarget(target: ClassificationTarget): ClassificationTarget {
  return {
    domain: target.domain.trim(),
    area: target.area.trim(),
    topic: target.topic.trim(),
  };
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
    title: "已复制论文文件夹路径",
    message: "当前 Web 环境不能直接打开本地文件夹，路径已复制到剪贴板。",
  };
}

function splitTags(value: string): string[] {
  return value
    .split(/[,\n，]/)
    .map((tag) => tag.trim())
    .filter(Boolean);
}
