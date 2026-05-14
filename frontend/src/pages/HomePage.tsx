import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchHomeDashboard,
  type BatchRecord,
  type HomeDashboardPayload,
  type PaperRecord,
} from "@/lib/api";
import { TopBar } from "@/components/layout/TopBar";
import { AppIcon, type AppIconName } from "@/components/ui/AppIcon";

const DEADLINES = [
  { name: "AAAI 2027", status: "TBD · watching" },
  { name: "ICCV 2027", status: "TBD · watching" },
  { name: "NeurIPS 2026", status: "TBD · watching" },
  { name: "ACL 2026", status: "TBD · watching" },
];

const JUMP_LINKS = [
  { to: "/overview", label: "Papers Overview", icon: "document" },
  { to: "/discover", label: "Discover", icon: "search" },
  { to: "/acquire", label: "Acquire", icon: "download" },
  { to: "/library", label: "Library", icon: "book" },
  { to: "/runtime", label: "Runtime", icon: "clock" },
  { to: "/logs", label: "Logs", icon: "list" },
] as const satisfies ReadonlyArray<{
  to: string;
  label: string;
  icon: AppIconName;
}>;

export function HomePage() {
  const [payload, setPayload] = useState<HomeDashboardPayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void fetchHomeDashboard()
      .then((data) => {
        if (!active) {
          return;
        }
        setPayload(data);
      })
      .catch((err: unknown) => {
        if (!active) {
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const totals = payload?.data.totals;
  const statusCounts = payload?.data.status_counts ?? {};
  const recentPapers = payload?.data.recent_papers ?? [];
  const queueItems = payload?.data.queue_items ?? [];
  const recentBatches = payload?.data.recent_batches ?? [];
  const totalPapers = totals?.papers ?? 0;
  const trackedStatusCount = Object.keys(statusCounts).length;

  const donut = useMemo(() => {
    const values = [totals?.curated ?? 0, totals?.library ?? 0, totals?.needs_review ?? 0];
    const total = values.reduce((sum, value) => sum + value, 0);
    if (total === 0) {
      return "conic-gradient(#eadff9 0deg 360deg)";
    }
    const angles = values.map((value) => (value / total) * 360);
    return `conic-gradient(
      #7f5af0 0deg ${angles[0]}deg,
      #b794f6 ${angles[0]}deg ${angles[0] + angles[1]}deg,
      #e9b949 ${angles[0] + angles[1]}deg 360deg
    )`;
  }, [totals]);

  const visibleQueue = useMemo(() => {
    const merged = [...queueItems, ...recentPapers];
    const seen = new Set<string>();
    const items: PaperRecord[] = [];
    for (const paper of merged) {
      if (seen.has(paper.paper_id)) {
        continue;
      }
      seen.add(paper.paper_id);
      items.push(paper);
    }
    return items.slice(0, 5);
  }, [queueItems, recentPapers]);

  const focusLabels = useMemo(() => {
    const values = [
      ...recentPapers.map((paper) => paper.topic),
      ...recentPapers.map((paper) => paper.area),
      ...recentPapers.map((paper) => paper.domain),
    ]
      .map((value) => value.trim())
      .filter(Boolean);
    return Array.from(new Set(values)).slice(0, 3);
  }, [recentPapers]);

  const statTiles = [
    { label: "Search", icon: "search", value: loading ? "..." : String(totals?.batches ?? 0) },
    { label: "Curated", icon: "list", value: loading ? "..." : String(totals?.curated ?? 0) },
    { label: "Final", icon: "book", value: loading ? "..." : String(totals?.library ?? 0) },
    { label: "Processed", icon: "check", value: loading ? "..." : String(totals?.processed ?? 0) },
    { label: "Needs Review", icon: "clock", value: loading ? "..." : String(totals?.needs_review ?? 0) },
    { label: "Failed", icon: "alert", value: loading ? "..." : String(totals?.failed ?? 0) },
  ] as const satisfies ReadonlyArray<{
    label: string;
    icon: AppIconName;
    value: string;
  }>;

  return (
    <>
      <TopBar current="Home" title="Home" />
      <main className="page">
        <section className="hero-card">
          <div className="hero-copy">
            <h1>HomePage 总入口</h1>
            <p>
              此页仅保留核心状态、近期异常、会议节点和 Dashboard 跳转，
              从这里快速掌握研究进度，进入各个工作台。
            </p>
            <div className="hero-actions">
              <Link className="primary-button" to="/library">
                Open Papers
              </Link>
              <Link className="ghost-button" to="/acquire">
                Open Queue
              </Link>
            </div>
          </div>
          <div className="hero-visual">
            <div className="visual-halo" />
            <div className="visual-orb orb-a" />
            <div className="visual-orb orb-b" />
            <div className="visual-orb orb-c" />
            <div className="visual-book" />
            <div className="visual-book-shadow" />
            <div className="visual-sheet visual-sheet-a" />
            <div className="visual-sheet visual-sheet-b" />
            <div className="visual-stack" />
            <div className="visual-card" />
            <div className="visual-note">note · idea · method · result</div>
          </div>
        </section>

        {error ? <div className="error-banner">{error}</div> : null}

        <section className="grid-row grid-row-main">
          <div className="panel-card">
            <h2>文献总览统计</h2>
            <div className="stat-grid">
              {statTiles.map((tile) => (
                <StatTile icon={tile.icon} key={tile.label} label={tile.label} value={tile.value} />
              ))}
            </div>
          </div>

          <div className="panel-card">
            <h2>研究信息</h2>
            <div className="insight-layout">
              <div className="insight-list">
                <InfoRow label="Search" value={totals?.batches ?? 0} />
                <InfoRow label="Curated" value={totals?.curated ?? 0} />
                <InfoRow label="Final" value={totals?.library ?? 0} />
                <InfoRow label="Needs Review" value={totals?.needs_review ?? 0} />
              </div>
              <div className="donut-wrap">
                <div className="donut" style={{ background: donut }}>
                  <div className="donut-inner">
                    <span>总计</span>
                    <strong>{totals?.papers ?? 0}</strong>
                  </div>
                </div>
              </div>
              <div className="meta-list">
                <MetaItem icon="spark" label="管线组成">
                  {`${totalPapers} 个文献条目，覆盖 ${trackedStatusCount} 个状态。`}
                </MetaItem>
                <MetaItem icon="search" label="研究聚焦">
                  {focusLabels.length > 0 ? `${focusLabels.join("、")} 等方向。` : "等待更多标签与分类补全。"}
                </MetaItem>
                <MetaItem icon="calendar" label="最近更新">
                  {recentPapers.length > 0
                    ? `${formatDate(recentPapers[0].updated_at)} 更新了 ${recentPapers.length} 条首页数据。`
                    : "暂无最近更新记录。"}
                </MetaItem>
              </div>
            </div>
          </div>

          <div className="panel-card">
            <h2>重要会议 DDL 总览</h2>
            <ul className="ddl-list">
              {DEADLINES.map((item) => (
                <li key={item.name}>
                  <div className="ddl-main">
                    <span className="ddl-icon">
                      <AppIcon name="calendar" size={18} />
                    </span>
                    <span>{item.name}</span>
                  </div>
                  <em>{item.status}</em>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="grid-row grid-row-bottom">
          <div className="panel-card wide">
            <div className="panel-head">
              <h2>近期待办</h2>
              <span className="panel-subtitle">优先处理异常和待审核条目</span>
            </div>
            <div className="queue-list">
              {visibleQueue.length > 0 ? (
                visibleQueue.map((paper) => (
                  <div key={paper.paper_id} className="queue-item">
                    <div className="queue-marker">
                      <AppIcon name="document" size={18} />
                    </div>
                    <div className="queue-main">
                      <strong>{paper.title}</strong>
                      <span>{paperSummary(paper)}</span>
                    </div>
                    <div className="queue-badges">
                      <span className={`badge badge-${badgeTone(paper.status)}`}>
                        {humanizeStatus(paper.status)}
                      </span>
                      <span className="badge badge-muted">{paper.area || paper.domain || "unclassified"}</span>
                      <span className="badge badge-light">{humanizeStage(paper.stage)}</span>
                    </div>
                    <div className="queue-arrow">
                      <AppIcon name="arrow-right" size={18} />
                    </div>
                  </div>
                ))
              ) : (
                <div className="queue-empty">当前没有待处理条目。</div>
              )}
            </div>
            <Link className="panel-footer-link" to="/acquire">
              查看全部待办
              <AppIcon name="arrow-right" size={16} />
            </Link>
          </div>

          <div className="panel-card compact">
            <h2>Dashboard 跳转</h2>
            <nav className="jump-list">
              {JUMP_LINKS.map((item) => (
                <Link className="jump-link" key={item.to} to={item.to}>
                  <div className="jump-link-main">
                    <span className="jump-link-icon">
                      <AppIcon name={item.icon} size={18} />
                    </span>
                    <span>{item.label}</span>
                  </div>
                  <span className="jump-link-arrow">
                    <AppIcon name="arrow-right" size={16} />
                  </span>
                </Link>
              ))}
            </nav>
            <div className="batch-preview">
              <h3>Recent Batches</h3>
              {recentBatches.length > 0 ? (
                recentBatches.slice(0, 3).map((batch) => (
                  <BatchRow batch={batch} key={batch.batch_id} />
                ))
              ) : (
                <div className="queue-empty">暂无 Search Batch 样本。</div>
              )}
            </div>
          </div>
        </section>
        <footer className="page-footer">Built with local paper library · For researchers, by researchers.</footer>
      </main>
    </>
  );
}

function StatTile(props: { icon: AppIconName; label: string; value: string }) {
  return (
    <div className="stat-tile">
      <div className="stat-tile-head">
        <span className="stat-tile-icon">
          <AppIcon name={props.icon} size={18} />
        </span>
      </div>
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </div>
  );
}

function InfoRow(props: { label: string; value: number }) {
  return (
    <div className="info-row">
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </div>
  );
}

function MetaItem(props: { children: string; icon: AppIconName; label: string }) {
  return (
    <div className="meta-item">
      <span className="meta-icon">
        <AppIcon name={props.icon} size={16} />
      </span>
      <div className="meta-copy">
        <strong>{props.label}</strong>
        <span>{props.children}</span>
      </div>
    </div>
  );
}

function BatchRow(props: { batch: BatchRecord }) {
  return (
    <div className="batch-row">
      <div className="batch-copy">
        <strong>{prettyBatchTitle(props.batch.batch_id)}</strong>
        <small>
          {props.batch.review_status} · {props.batch.candidate_total} candidates
        </small>
      </div>
      <em>{props.batch.keep_total} keep</em>
    </div>
  );
}

function badgeTone(status: string): string {
  if (status === "processed") {
    return "success";
  }
  if (status === "needs-review") {
    return "warning";
  }
  if (status === "failed") {
    return "danger";
  }
  return "muted";
}

function humanizeStatus(status: string): string {
  if (status === "needs-review") {
    return "needs review";
  }
  if (status === "needs-pdf") {
    return "needs pdf";
  }
  return status;
}

function humanizeStage(stage: string): string {
  if (stage === "acquire") {
    return "queue";
  }
  if (stage === "library") {
    return "library";
  }
  return stage || "unknown";
}

function paperSummary(paper: PaperRecord): string {
  const parts = [paper.venue, paper.year ? String(paper.year) : "", paper.topic || paper.area || paper.domain]
    .map((value) => value.trim())
    .filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : "Metadata pending";
}

function prettyBatchTitle(batchId: string): string {
  return batchId.replace(/-/g, " ");
}

function formatDate(value: string): string {
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
