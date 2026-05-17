import type { PaperRecord } from "@/lib/api";
import { type StatusTone } from "@/lib/format";

export type LibraryTabKey = "all" | "needs_pdf" | "pending_refine" | "reading_queue" | "reviewed" | "more";
export type LibraryViewMode = "list" | "grid";

export type LibraryCollectionId =
  | "all"
  | "recently_added"
  | "needs_pdf"
  | "pending_refine"
  | "reading_queue"
  | "reviewed"
  | "starred";

export type LibraryExtraFilterId = "starred" | "has_notes" | "no_tags" | "updated_7d" | "updated_30d";

export type LibraryCollectionNode = {
  id: LibraryCollectionId;
  label: string;
  count: number;
  level: "root" | "item";
};

export type LibraryCollectionTree = {
  root: LibraryCollectionNode;
  items: LibraryCollectionNode[];
  quickFilters: Array<{ id: LibraryExtraFilterId; label: string; count: number }>;
};

export type LibraryWorkflowItem = {
  label: string;
  value: string;
  tone: StatusTone;
};

export type ResearchLogTask = {
  id: string;
  label: string;
  checked: boolean;
};

export type ResearchLogEntry = {
  id: string;
  timestamp: string;
  title: string;
  bullets: string[];
  nextSteps: string[];
  tasks: ResearchLogTask[];
};

const DAY_MS = 24 * 60 * 60 * 1000;

export function buildLibraryCollectionTree(papers: PaperRecord[], starredIds: Set<string>): LibraryCollectionTree {
  const root: LibraryCollectionNode = {
    id: "all",
    label: "我的图书馆",
    count: papers.length,
    level: "root",
  };

  return {
    root,
    items: [
      { id: "recently_added", label: "Recently Added", count: countByPredicate(papers, (paper) => inDays(paper.updated_at, 30)), level: "item" },
      { id: "needs_pdf", label: "Needs PDF", count: countByPredicate(papers, isMissingPdf), level: "item" },
      { id: "pending_refine", label: "Pending Refine", count: countByPredicate(papers, isPendingRefine), level: "item" },
      { id: "reading_queue", label: "Reading Queue", count: countByPredicate(papers, isReadingQueue), level: "item" },
      { id: "reviewed", label: "Reviewed", count: countByPredicate(papers, isReviewed), level: "item" },
      { id: "starred", label: "Starred", count: countByPredicate(papers, (paper) => isStarred(paper, starredIds)), level: "item" },
    ],
    quickFilters: [
      { id: "updated_7d", label: "本周更新", count: countByPredicate(papers, (paper) => inDays(paper.updated_at, 7)) },
      { id: "updated_30d", label: "近30天导入", count: countByPredicate(papers, (paper) => inDays(paper.updated_at, 30)) },
      { id: "no_tags", label: "未分类标签", count: countByPredicate(papers, (paper) => paper.tags.length === 0) },
    ],
  };
}

export function filterLibraryPapers(
  papers: PaperRecord[],
  options: {
    collectionId: LibraryCollectionId;
    query: string;
    tab: LibraryTabKey;
    starredIds: Set<string>;
    extraFilters: Set<LibraryExtraFilterId>;
  },
): PaperRecord[] {
  const needle = normalize(options.query);
  return papers.filter((paper) => {
    if (!matchesCollection(paper, options.collectionId, options.starredIds)) return false;
    if (!matchesTab(paper, options.tab)) return false;
    if (!matchesExtraFilters(paper, options.extraFilters, options.starredIds)) return false;
    if (!needle) return true;
    return paperText(paper).includes(needle);
  });
}

export function matchesCollection(paper: PaperRecord, collectionId: LibraryCollectionId, starredIds: Set<string>): boolean {
  switch (collectionId) {
    case "all":
      return true;
    case "recently_added":
      return inDays(paper.updated_at, 30);
    case "needs_pdf":
      return isMissingPdf(paper);
    case "pending_refine":
      return isPendingRefine(paper);
    case "reading_queue":
      return isReadingQueue(paper);
    case "reviewed":
      return isReviewed(paper);
    case "starred":
      return isStarred(paper, starredIds);
  }
}

export function matchesTab(paper: PaperRecord, tab: LibraryTabKey): boolean {
  switch (tab) {
    case "all":
    case "more":
      return true;
    case "needs_pdf":
      return isMissingPdf(paper);
    case "pending_refine":
      return isPendingRefine(paper);
    case "reading_queue":
      return isReadingQueue(paper);
    case "reviewed":
      return isReviewed(paper);
  }
}

export function matchesExtraFilters(paper: PaperRecord, filters: Set<LibraryExtraFilterId>, starredIds: Set<string>): boolean {
  for (const filter of filters) {
    if (filter === "starred" && !isStarred(paper, starredIds)) return false;
    if (filter === "has_notes" && !paper.note_path) return false;
    if (filter === "no_tags" && paper.tags.length > 0) return false;
    if (filter === "updated_7d" && !inDays(paper.updated_at, 7)) return false;
    if (filter === "updated_30d" && !inDays(paper.updated_at, 30)) return false;
  }
  return true;
}

export function paperSubtitle(paper: PaperRecord): string {
  return [
    paper.venue || "未填写期刊",
    paper.year ? String(paper.year) : "未填写年份",
    paper.topic || paper.area || paper.domain || "未填写方向",
  ].join(" / ");
}

export function buildWorkflowItems(paper: PaperRecord): LibraryWorkflowItem[] {
  const hasPdf = !isMissingPdf(paper);
  const parserTone: StatusTone = paper.parser_status === "parsed" ? "success" : paper.parser_status === "running" ? "warning" : "muted";
  const refineTone: StatusTone = paper.refined_review_status === "approved" ? "success" : isPendingRefine(paper) ? "warning" : "muted";
  const noteTone: StatusTone = paper.note_path || paper.note_status === "approved" ? "info" : "muted";
  const reviewTone: StatusTone = isReviewed(paper) ? "success" : "warning";

  return [
    { label: "PDF", value: hasPdf ? "PDF 就绪" : "PDF 缺失", tone: hasPdf ? "success" : "warning" },
    { label: "解析", value: paper.parser_status === "parsed" ? "已解析" : paper.parser_status === "running" ? "解析中" : "未解析", tone: parserTone },
    { label: "精读", value: paper.refined_review_status === "approved" ? "已精读" : isPendingRefine(paper) ? "待精读" : "未精读", tone: refineTone },
    { label: "笔记", value: paper.note_path || paper.note_status === "approved" ? "笔记更新" : "未更新", tone: noteTone },
    { label: "评审", value: isReviewed(paper) ? "已评审" : "待评审", tone: reviewTone },
  ];
}

export function buildWorkflowTimeline(paper: PaperRecord): Array<{ label: string; status: string; timestamp: string; tone: StatusTone }> {
  const base = safeDate(paper.updated_at);
  return buildWorkflowItems(paper).map((item, index) => ({
    label: item.label,
    status: item.value,
    timestamp: formatTimelineTime(offsetDate(base, index - 3)),
    tone: item.tone,
  }));
}

export function buildResearchLogs(paper: PaperRecord): ResearchLogEntry[] {
  void paper;
  return [];
}

export function formatTimelineTime(value: Date): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(value);
}

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function paperText(paper: PaperRecord): string {
  return normalize(
    [
      paper.title,
      paper.venue,
      paper.year ? String(paper.year) : "",
      paper.topic,
      paper.area,
      paper.domain,
      paper.doi,
      paper.path,
      paper.paper_path,
      paper.paper_id,
      paper.tags.join(" "),
    ].join(" "),
  );
}

function inDays(value: string, days: number): boolean {
  const time = new Date(value).getTime();
  return !Number.isNaN(time) && Date.now() - time <= days * DAY_MS;
}

function countByPredicate(papers: PaperRecord[], predicate: (paper: PaperRecord) => boolean): number {
  return papers.filter(predicate).length;
}

function isMissingPdf(paper: PaperRecord): boolean {
  return paper.asset_status === "missing_pdf" || !paper.paper_path;
}

function isPendingRefine(paper: PaperRecord): boolean {
  return paper.refined_review_status === "pending" || paper.workflow_status === "refine_review_pending";
}

function isReadingQueue(paper: PaperRecord): boolean {
  return paper.read_status !== "read" || paper.workflow_status === "note_review_pending" || paper.workflow_status === "refine_review_pending";
}

function isReviewed(paper: PaperRecord): boolean {
  return paper.review_status === "accepted" || paper.workflow_status === "reviewed" || paper.workflow_status === "processed";
}

function isStarred(paper: PaperRecord, starredIds: Set<string>): boolean {
  return paper.starred || starredIds.has(paper.paper_id);
}

function safeDate(value: string): Date {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
}

function offsetDate(base: Date, days: number): Date {
  return new Date(base.getTime() + days * DAY_MS);
}
