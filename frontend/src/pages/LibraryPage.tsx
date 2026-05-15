import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { TopBar } from "@/components/layout/TopBar";
import { AppIcon } from "@/components/ui/AppIcon";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { fetchLibraryDashboard, type LibraryDashboardData, type PaperRecord } from "@/lib/api";
import { paperSummary } from "@/lib/format";
import { matchesLibraryFilter, type LibraryFilter } from "@/lib/paperWorkflow";

export function LibraryPage() {
  const [data, setData] = useState<LibraryDashboardData | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<LibraryFilter>("all");
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    void fetchLibraryDashboard().then((payload) => setData(payload.data));
  }, []);

  const papers = data?.papers ?? [];
  const filtered = useMemo(() => {
    const needle = deferredQuery.trim().toLowerCase();
    return papers.filter((paper) => {
      const statusMatch = matchesLibraryFilter(paper, status);
      const text = `${paper.title} ${paper.domain} ${paper.area} ${paper.topic} ${paper.venue}`.toLowerCase();
      return statusMatch && (!needle || text.includes(needle));
    });
  }, [deferredQuery, papers, status]);

  const summary = data?.summary ?? {};
  const domains = domainCounts(papers).slice(0, 8);
  const years = yearCounts(papers).slice(0, 8);

  return (
    <>
      <TopBar current="Library" section="Research Workspace > Library" title="Library" />
      <main className="page library-page">
        <section className="workflow-hero library-hero">
          <div className="workflow-hero-icon">
            <AppIcon name="book" size={40} />
          </div>
          <div>
            <h1>Library Overview</h1>
            <p>Review accepted papers, parse health, and classification coverage from the single library view.</p>
          </div>
        </section>

        <section className="metric-strip">
          <Metric icon="document" label="Library Papers" value={summary.library_total ?? 0} />
          <Metric icon="check" label="Accepted" value={summary.processed_total ?? 0} />
          <Metric icon="clock" label="Pending Review" value={summary.needs_review_total ?? 0} />
          <Metric icon="folder" label="Unclassified" value={summary.unclassified_total ?? 0} />
        </section>

        <section className="grid-row library-insights">
          <Insight title="By Domain" rows={domains} />
          <Insight title="By Year" rows={years} />
          <div className="panel-card compact">
            <h2>Quick Links</h2>
            <Link className="jump-link" to="/discover?view=acquire">
              <span>Open Acquire Queue</span>
              <AppIcon name="arrow-right" size={16} />
            </Link>
            <Link className="jump-link" to="/config">
              <span>Open Config Health</span>
              <AppIcon name="arrow-right" size={16} />
            </Link>
          </div>
        </section>

        <section className="panel-card table-panel">
          <div className="panel-head">
            <h2>Recent Papers</h2>
            <div className="filter-row">
              <input
                aria-label="Search library papers"
                placeholder="Search title, domain, area, topic, or venue"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <select aria-label="Filter library papers" value={status} onChange={(event) => setStatus(event.target.value as LibraryFilter)}>
                <option value="all">All Status</option>
                <option value="accepted">Accepted</option>
                <option value="pending-review">Pending Review</option>
                <option value="parsed">Parsed</option>
                <option value="missing-pdf">Missing PDF</option>
                <option value="parse-failed">Parse Failed</option>
              </select>
            </div>
          </div>
          <div className="data-table library-table">
            <div className="data-row data-head">
              <span>Paper</span>
              <span>Year</span>
              <span>Venue</span>
              <span>Status</span>
              <span>Tags</span>
              <span>Open</span>
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
      <Link to={`/library/${encodeURIComponent(paper.paper_id)}`}>Detail</Link>
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
