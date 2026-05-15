import type { PaperRecord } from "@/lib/api";

export function humanizeStatus(status: string): string {
  switch (status) {
    case "needs-review":
      return "待审核";
    case "needs-pdf":
      return "缺少 PDF";
    case "parse-pending":
      return "待解析";
    case "parse-failed":
      return "解析失败";
    case "processed":
      return "已处理";
    case "rejected":
      return "已删除";
    case "reviewed":
      return "已审核";
    case "pending":
      return "待处理";
    case "active":
      return "进行中";
    case "completed":
      return "已完成";
    case "queued":
      return "已排队";
    case "template":
      return "已生成模板";
    case "success":
      return "成功";
    case "failed":
      return "失败";
    default:
      return status || "未知";
  }
}

export function statusTone(status: string): string {
  if (["processed", "completed", "reviewed", "success"].includes(status)) {
    return "success";
  }
  if (["needs-review", "needs-pdf", "parse-pending", "queued", "pending", "active", "template"].includes(status)) {
    return "warning";
  }
  if (["failed", "parse-failed", "rejected"].includes(status)) {
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
