import type { PaperRecord } from "@/lib/api";

export function humanizeStatus(status: string): string {
  if (status === "needs-review") {
    return "待审核";
  }
  if (status === "needs-pdf") {
    return "缺少 PDF";
  }
  if (status === "parse-failed") {
    return "解析失败";
  }
  if (status === "processed") {
    return "已处理";
  }
  if (status === "rejected") {
    return "已拒绝";
  }
  return status || "未知";
}

export function statusTone(status: string): string {
  if (status === "processed") {
    return "success";
  }
  if (status === "needs-review" || status === "needs-pdf" || status === "parse-pending") {
    return "warning";
  }
  if (status === "failed" || status === "parse-failed" || status === "rejected") {
    return "danger";
  }
  return "muted";
}

export function paperSummary(paper: PaperRecord): string {
  const parts = [paper.venue, paper.year ? String(paper.year) : "", paper.topic || paper.area || paper.domain]
    .map((value) => value.trim())
    .filter(Boolean);
  return parts.length > 0 ? parts.join(" | ") : "元数据待补充";
}

export function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(parsed);
}
