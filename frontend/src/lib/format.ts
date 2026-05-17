import type { CandidateRecord, PaperRecord } from "@/lib/api";

export type StatusTone = "success" | "info" | "warning" | "danger" | "muted";

const STATUS_LABELS: Record<string, string> = {
  accepted: "已收录",
  active: "进行中",
  completed: "已完成",
  failed: "失败",
  keep: "已收录",
  missing: "缺失",
  missing_pdf: "缺少 PDF",
  needs_pdf: "缺少 PDF",
  needs_review: "待审阅",
  not_started: "待解析",
  note_missing: "待生成 LLM Note",
  note_rejected: "Note 需修改",
  note_review_pending: "待审核 Note",
  parsed: "已解析",
  pending: "待处理",
  processed: "已处理",
  queued: "已排队",
  read: "已读",
  rejected: "已归档",
  reviewed: "已审阅",
  refine_rejected: "Refine 需修改",
  refine_review_pending: "待审核 Refine",
  running: "运行中",
  ready: "已就绪",
  success: "成功",
  template: "已生成模板",
  unclassified: "未分类",
  unread: "未读",
  "needs-pdf": "缺少 PDF",
  "needs-review": "待审阅",
  "parse-failed": "解析失败",
  "parse-pending": "待解析",
  pdf_ready: "PDF 就绪",
};

export function humanizeStatus(status: string): string {
  return STATUS_LABELS[status] ?? status ?? "未知";
}

export function statusTone(status: string): StatusTone {
  if (["processed", "completed", "reviewed", "success", "parsed", "accepted", "keep", "pdf_ready", "read", "ready"].includes(status)) {
    return "success";
  }
  if (["running", "active"].includes(status)) {
    return "info";
  }
  if (["needs-review", "needs_review", "needs-pdf", "needs_pdf", "missing_pdf", "parse-pending", "not_started", "queued", "pending", "template", "missing", "unread", "unclassified", "note_missing", "note_review_pending", "refine_review_pending"].includes(status)) {
    return "warning";
  }
  if (["failed", "parse-failed", "rejected", "refine_rejected", "note_rejected"].includes(status)) {
    return "danger";
  }
  return "muted";
}

export function paperSummary(paper: PaperRecord): string {
  const parts = [paper.venue, paper.year ? String(paper.year) : "", paper.topic || paper.area || paper.domain]
    .map((value) => value.trim())
    .filter(Boolean);
  return parts.length > 0 ? parts.join(" / ") : "元数据待补充";
}

export function candidateSummary(candidate: CandidateRecord): string {
  const parts = [candidate.venue, candidate.year ? String(candidate.year) : "", candidate.source_type]
    .map((value) => value.trim())
    .filter(Boolean);
  return parts.length > 0 ? parts.join(" / ") : "候选元数据待补充";
}

export function authorsText(authors: string[] | undefined, fallback = "作者待补充"): string {
  if (!authors || authors.length === 0) {
    return fallback;
  }
  if (authors.length <= 3) {
    return authors.join(", ");
  }
  return `${authors.slice(0, 3).join(", ")} et al.`;
}

export function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value || "未填写";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(parsed);
}

export function compactNumber(value: number | undefined): string {
  return new Intl.NumberFormat("zh-CN", { notation: "compact" }).format(value ?? 0);
}

export function middleEllipsis(value: string, head = 28, tail = 18): string {
  if (value.length <= head + tail + 3) {
    return value;
  }
  return `${value.slice(0, head)}...${value.slice(-tail)}`;
}
