import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { AppIcon } from "@/components/ui/AppIcon";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { fetchLibraryDashboard, type LibraryDashboardData, type PaperRecord } from "@/lib/api";
import { paperSummary } from "@/lib/format";

export function LibraryPage() {
  const [data, setData] = useState<LibraryDashboardData | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    void fetchLibraryDashboard().then((payload) => setData(payload.data));
  }, []);

  const papers = data?.papers ?? [];
  const filtered = useMemo(() => {
    const needle = deferredQuery.trim().toLowerCase();
    return papers.filter((paper) => {
      const statusMatch = status === "all" || paper.status === status;
      const text = `${paper.title} ${paper.domain} ${paper.area} ${paper.topic} ${paper.venue}`.toLowerCase();
      return statusMatch && (!needle || text.includes(needle));
    });
  }, [deferredQuery, papers, status]);

  const summary = data?.summary ?? {};
  const domains = domainCounts(papers).slice(0, 8);
  const years = yearCounts(papers).slice(0, 8);

  return (
    <>
      <TopBar current="论文库" section="研究工作台 > 论文库" title="论文库" />
      <main className="page library-page">
        <section className="workflow-hero library-hero">
          <div className="workflow-hero-icon">
            <AppIcon name="book" size={40} />
          </div>
          <div>
            <h1>当前论文库总览</h1>
            <p>查看已入库论文、解析状态和分类结构，支持继续跳转到论文详情页。</p>
          </div>
        </section>
        <section className="metric-strip">
          <Metric icon="document" label="论文总数" value={summary.library_total ?? 0} />
          <Metric icon="check" label="已处理" value={summary.processed_total ?? 0} />
          <Metric icon="clock" label="待审核" value={summary.needs_review_total ?? 0} />
          <Metric icon="folder" label="未分类" value={summary.unclassified_total ?? 0} />
        </section>
        <section className="grid-row library-insights">
          <Insight title="按 Domain 分布" rows={domains} />
          <Insight title="按年份分布" rows={years} />
          <div className="panel-card compact">
            <h2>常用操作</h2>
            <Link className="jump-link" to="/discover?view=acquire">
              <span>打开获取队列</span>
              <AppIcon name="arrow-right" size={16} />
            </Link>
            <Link className="jump-link" to="/config">
              <span>查看配置健康度</span>
              <AppIcon name="arrow-right" size={16} />
            </Link>
          </div>
        </section>
        <section className="panel-card table-panel">
          <div className="panel-head">
            <h2>最近论文</h2>
            <div className="filter-row">
              <input aria-label="搜索论文" placeholder="搜索标题、领域、主题..." value={query} onChange={(event) => setQuery(event.target.value)} />
              <select aria-label="状态筛选" value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="all">全部状态</option>
                <option value="processed">已处理</option>
                <option value="needs-review">待审核</option>
                <option value="needs-pdf">缺少 PDF</option>
                <option value="parse-failed">解析失败</option>
              </select>
            </div>
          </div>
          <div className="data-table library-table">
            <div className="data-row data-head">
              <span>论文标题</span>
              <span>年份</span>
              <span>Venue</span>
              <span>状态</span>
              <span>标签</span>
              <span>查看</span>
            </div>
            {filtered.map((paper) => (
              <PaperRow key={paper.paper_id} paper={paper} />
            ))}
          </div>
        </section>
      </main>
    </>
  );
}

function PaperRow({ paper }: { paper: PaperRecord }) {
  return (
    <div className="data-row">
      <span>
        <strong>{paper.title}</strong>
        <small>{paperSummary(paper)}</small>
      </span>
      <span>{paper.year ?? "-"}</span>
      <span>{paper.venue || "-"}</span>
      <span>
        <StatusBadge status={paper.status} />
      </span>
      <span className="tag-list">{paper.tags.slice(0, 3).map((tag) => <em key={tag}>{tag}</em>)}</span>
      <Link to={`/library/${encodeURIComponent(paper.paper_id)}`}>详情</Link>
    </div>
  );
}

function Metric(props: { icon: "document" | "check" | "clock" | "folder"; label: string; value: number }) {
  return (
    <div className="metric-card">
      <span className="stat-tile-icon">
        <AppIcon name={props.icon} size={18} />
      </span>
      <div>
        <span>{props.label}</span>
        <strong>{props.value}</strong>
      </div>
    </div>
  );
}

function Insight(props: { title: string; rows: Array<[string, number]> }) {
  const max = Math.max(...props.rows.map((row) => row[1]), 1);

  return (
    <div className="panel-card insight-card">
      <h2>{props.title}</h2>
      {props.rows.map(([label, value]) => (
        <div className="bar-row" key={label}>
          <span>{label || "unclassified"}</span>
          <i>
            <b style={{ width: `${(value / max) * 100}%` }} />
          </i>
          <em>{value}</em>
        </div>
      ))}
    </div>
  );
}

function domainCounts(papers: PaperRecord[]): Array<[string, number]> {
  return counts(papers.map((paper) => paper.domain || "unclassified"));
}

function yearCounts(papers: PaperRecord[]): Array<[string, number]> {
  return counts(papers.map((paper) => String(paper.year ?? "unknown")));
}

function counts(values: string[]): Array<[string, number]> {
  const map = new Map<string, number>();
  for (const value of values) {
    map.set(value, (map.get(value) ?? 0) + 1);
  }
  return Array.from(map.entries()).sort((left, right) => right[1] - left[1]);
}
