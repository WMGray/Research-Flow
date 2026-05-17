import type { PaperRecord } from "@/lib/api";
import { type StatusTone } from "@/lib/format";

export type DetailTabKey = "overview" | "notes" | "info";

export type DetailWorkflowItem = {
  key: "pdf" | "parser" | "refine" | "note" | "review";
  label: string;
  status: string;
  tone: StatusTone;
  timestamp: string;
  targetTab: DetailTabKey;
};

export type ResearchLogItem = {
  id: string;
  timestamp: string;
  title: string;
  bullets: string[];
  nextSteps: string[];
  tasks: Array<{ id: string; label: string; checked: boolean }>;
};

export type FileResource = {
  id: "pdf" | "note" | "refined";
  label: string;
  status: string;
  tone: StatusTone;
  fileName: string;
  path: string;
};

const DAY_MS = 24 * 60 * 60 * 1000;

export function buildDetailAuthors(paper: PaperRecord): string[] {
  return paper.authors ?? [];
}

export function compactAuthors(authors: string[]): string {
  if (authors.length === 0) return "未填写";
  if (authors.length <= 3) return authors.join(", ");
  return `${authors.slice(0, 3).join(", ")} +${authors.length - 3}`;
}

export function buildEvidenceAbstract(paper: PaperRecord): string {
  return paper.abstract || paper.summary || "暂无真实摘要。请刷新元数据，或在 metadata 中补充 abstract/summary。";
}

export function buildDetailWorkflow(paper: PaperRecord): DetailWorkflowItem[] {
  const base = safeDate(paper.updated_at);
  const pdfReady = hasPdf(paper);
  const parsed = paper.parser_status === "parsed" || Boolean(paper.parsed_text_path || paper.parsed_sections_path);
  const parserFailed = paper.parser_status === "failed" || paper.workflow_status === "parse-failed";
  const parserRunning = ["running", "queued", "active"].includes(paper.parser_status);
  const refinedReady = paper.refined_review_status === "approved" || Boolean(paper.refined_path || paper.parser_artifacts?.refined_path);
  const refinePending = paper.refined_review_status === "pending" || paper.workflow_status === "refine_review_pending";
  const hasNote = hasGeneratedNote(paper);
  const reviewed = isReviewed(paper);

  return [
    {
      key: "pdf",
      label: "PDF",
      status: pdfReady ? "PDF 就绪" : "PDF 缺失",
      tone: pdfReady ? "success" : "muted",
      timestamp: formatDateTime(offsetDate(base, -3)),
      targetTab: "overview",
    },
    {
      key: "parser",
      label: "解析",
      status: parserFailed ? "解析失败" : parsed ? "已解析" : parserRunning ? "解析中" : "未解析",
      tone: parserFailed ? "danger" : parsed ? "success" : parserRunning ? "warning" : "muted",
      timestamp: formatDateTime(offsetDate(base, -2)),
      targetTab: "overview",
    },
    {
      key: "refine",
      label: "精读",
      status: refinedReady ? "已精读" : paper.read_status === "reading" ? "阅读中" : refinePending ? "待精读" : "待精读",
      tone: refinedReady ? "success" : refinePending || paper.read_status === "reading" ? "warning" : "muted",
      timestamp: formatDateTime(offsetDate(base, -1)),
      targetTab: "notes",
    },
    {
      key: "note",
      label: "笔记",
      status: hasNote ? "笔记更新" : "无笔记",
      tone: hasNote ? "info" : "muted",
      timestamp: formatDateTime(base),
      targetTab: hasNote ? "notes" : "notes",
    },
    {
      key: "review",
      label: "评审",
      status: reviewed ? "已评审" : "待评审",
      tone: reviewed ? "success" : "warning",
      timestamp: formatDateTime(offsetDate(base, 1)),
      targetTab: "overview",
    },
  ];
}

export function buildResearchLogs(paper: PaperRecord): ResearchLogItem[] {
  void paper;
  return [];
}

export function buildNoteStatusRows(paper: PaperRecord): Array<{ label: string; value: string; meta?: string }> {
  return [
    { label: "Note", value: hasGeneratedNote(paper) ? "已生成" : "未生成", meta: hasGeneratedNote(paper) ? formatDateTime(safeDate(paper.updated_at)) : undefined },
    { label: "Refined", value: hasRefinedSummary(paper) ? "已生成" : "未生成", meta: hasRefinedSummary(paper) ? formatDateTime(safeDate(paper.updated_at)) : undefined },
    { label: "来源", value: hasPdf(paper) ? "metadata + PDF parse" : "metadata" },
  ];
}

export function buildNotePreview(paper: PaperRecord): string[] {
  if (paper.summary) return [paper.summary];
  return ["暂无真实 Note 预览。生成或编辑 note.md 后，这里会显示真实 artifact 内容。"];
}

export function buildRefinedSummary(paper: PaperRecord): string[] {
  if (paper.summary) return [paper.summary];
  return ["暂无真实 Refined Summary。解析 PDF 或补充 summary 后，这里会显示真实内容。"];
}

export function buildFileResources(paper: PaperRecord): FileResource[] {
  return [
    buildResource("pdf", "PDF", hasPdf(paper) ? "就绪" : "缺失", hasPdf(paper) ? "success" : "muted", paper.paper_path, "paper.pdf"),
    buildResource("refined", "Parse", hasRefinedSummary(paper) ? "已生成" : "未生成", hasRefinedSummary(paper) ? "success" : "muted", paper.refined_path || paper.parser_artifacts?.refined_path || paper.parsed_text_path || paper.parsed_sections_path || "", "parsed.md"),
    buildResource("note", "LLM Note", hasGeneratedNote(paper) ? "已生成" : "未生成", hasGeneratedNote(paper) ? "success" : "muted", paper.note_path, "note.md"),
  ];
}

export function hasGeneratedNote(paper: PaperRecord): boolean {
  return Boolean(paper.note_path) || paper.note_status === "approved";
}

export function hasRefinedSummary(paper: PaperRecord): boolean {
  return Boolean(paper.refined_path || paper.parser_artifacts?.refined_path) || paper.refined_review_status === "approved";
}

export function hasPdf(paper: PaperRecord): boolean {
  return paper.asset_status !== "missing_pdf" && Boolean(paper.paper_path);
}

export function formatDateTime(value: Date | string): string {
  const parsed = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(parsed.getTime())) return "未填写";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parsed);
}

function buildResource(
  id: FileResource["id"],
  label: string,
  status: string,
  tone: StatusTone,
  path: string,
  fallbackName: string,
): FileResource {
  return {
    id,
    label,
    status,
    tone,
    fileName: path ? fileNameFromPath(path) : fallbackName,
    path,
  };
}

function fileNameFromPath(path: string): string {
  const parts = path.split(/[\\/]+/).filter(Boolean);
  return parts.at(-1) || path;
}

function isReviewed(paper: PaperRecord): boolean {
  return paper.review_status === "accepted" || paper.workflow_status === "reviewed" || paper.workflow_status === "processed";
}

function safeDate(value: string): Date {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
}

function offsetDate(base: Date, days: number): Date {
  return new Date(base.getTime() + days * DAY_MS);
}
