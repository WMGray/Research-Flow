import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { AppIcon, type AppIconName } from "@/components/ui/AppIcon";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  fetchHomeDashboard,
  type APIEnvelope,
  type BatchRecord,
  type HomeDashboardData,
  type PaperRecord,
} from "@/lib/api";
import { formatDate, paperSummary } from "@/lib/format";

const DEADLINES = [
  { name: "AAAI 2027", status: "跟踪中" },
  { name: "ICCV 2027", status: "跟踪中" },
  { name: "NeurIPS 2026", status: "跟踪中" },
  { name: "ACL 2026", status: "跟踪中" },
];

const JUMP_LINKS = [
  { to: "/discover", label: "Workflow 总览", icon: "search" },
  { to: "/discover?view=acquire", label: "获取队列", icon: "download" },
  { to: "/config", label: "系统配置", icon: "settings" },
] as const satisfies ReadonlyArray<{
  to: string;
  label: string;
  icon: AppIconName;
}>;

export function HomePage() {
  const [payload, setPayload] = useState<APIEnvelope<HomeDashboardData> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    void fetchHomeDashboard()
      .then((data) => {
        if (active) {
          setPayload(data);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "加载首页看板失败");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
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

  const donut = useMemo(() => {
    const values = [totals?.curated ?? 0, totals?.library ?? 0, totals?.needs_review ?? 0];
    const total = values.reduce((sum, value) => sum + value, 0);

    if (total === 0) {
      return "conic-gradient(#e6deff 0deg 360deg)";
    }

    const first = (values[0] / total) * 360;
    const second = first + (values[1] / total) * 360;

    return `conic-gradient(
      #6f5bff 0deg ${first}deg,
      #98c6ff ${first}deg ${second}deg,
      #82d7b3 ${second}deg 360deg
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
    const labels = [
      ...recentPapers.map((paper) => paper.topic),
      ...recentPapers.map((paper) => paper.area),
      ...recentPapers.map((paper) => paper.domain),
    ]
      .map((value) => value.trim())
      .filter(Boolean);

    return Array.from(new Set(labels)).slice(0, 3);
  }, [recentPapers]);

  const statTiles = [
    { label: "检索批次", icon: "search", value: loading ? "..." : String(totals?.batches ?? 0) },
    { label: "获取队列", icon: "list", value: loading ? "..." : String(totals?.curated ?? 0) },
    { label: "已入库", icon: "book", value: loading ? "..." : String(totals?.library ?? 0) },
    { label: "已处理", icon: "check", value: loading ? "..." : String(totals?.processed ?? 0) },
    { label: "待审核", icon: "clock", value: loading ? "..." : String(totals?.needs_review ?? 0) },
    { label: "解析失败", icon: "alert", value: loading ? "..." : String(totals?.parse_failed ?? 0) },
    { label: "失败状态", icon: "alert", value: loading ? "..." : String(totals?.failed ?? 0) },
  ] as const satisfies ReadonlyArray<{
    label: string;
    icon: AppIconName;
    value: string;
  }>;

  return (
    <>
      <TopBar current="首页" title="首页" />
      <main className="page">
        <section className="hero-card">
          <div className="hero-copy">
            <h1>研究流程总览中枢</h1>
            <p>统一跟踪论文从检索、筛选、获取、解析到审核的全链路状态，减少切页和上下文丢失。</p>
            <div className="hero-actions">
              <Link className="primary-button" to="/discover">
                打开 Workflow
              </Link>
              <Link className="ghost-button" to="/discover?view=acquire">
                打开获取队列
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
            <div className="visual-note">检索 | 获取 | 解析 | 审核</div>
          </div>
        </section>

        {error ? <div className="error-banner">{error}</div> : null}

        <section className="grid-row grid-row-main">
          <div className="panel-card">
            <h2>论文流程概览</h2>
            <div className="stat-grid">
              {statTiles.map((tile) => (
                <StatTile icon={tile.icon} key={tile.label} label={tile.label} value={tile.value} />
              ))}
            </div>
          </div>

          <div className="panel-card">
            <h2>研究快照</h2>
            <div className="insight-layout">
              <div className="insight-list">
                <InfoRow label="检索批次" value={totals?.batches ?? 0} />
                <InfoRow label="获取队列" value={totals?.curated ?? 0} />
                <InfoRow label="已入库论文" value={totals?.library ?? 0} />
                <InfoRow label="待审核" value={totals?.needs_review ?? 0} />
              </div>
              <div className="donut-wrap">
                <div className="donut" style={{ background: donut }}>
                  <div className="donut-inner">
                    <span>论文总量</span>
                    <strong>{totals?.papers ?? 0}</strong>
                  </div>
                </div>
              </div>
              <div className="meta-list">
                <MetaItem icon="spark" label="状态覆盖">
                  {`当前共有 ${totals?.papers ?? 0} 条记录，分布在 ${Object.keys(statusCounts).length} 个流程状态中。`}
                </MetaItem>
                <MetaItem icon="search" label="当前关注">
                  {focusLabels.length > 0 ? focusLabels.join(" | ") : "继续补充元数据后，这里会更准确地展示当前研究聚焦。"}
                </MetaItem>
                <MetaItem icon="calendar" label="最近更新">
                  {recentPapers.length > 0 ? `${formatDate(recentPapers[0].updated_at)} 完成最近一次论文同步。` : "当前还没有最近更新记录。"}
                </MetaItem>
              </div>
            </div>
          </div>

          <div className="panel-card">
            <h2>会议信号</h2>
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
              <h2>重点处理队列</h2>
              <span className="panel-subtitle">优先关注缺少 PDF、解析失败或待审核的论文。</span>
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
                      <StatusBadge status={paper.status} />
                      <span className="badge badge-muted">{paper.area || paper.domain || "unclassified"}</span>
                      <span className="badge badge-light">{humanizeStage(paper.stage)}</span>
                    </div>
                    <div className="queue-arrow">
                      <AppIcon name="arrow-right" size={18} />
                    </div>
                  </div>
                ))
              ) : (
                <div className="queue-empty">当前没有需要优先处理的论文。</div>
              )}
            </div>
            <Link className="panel-footer-link" to="/discover?view=acquire">
              打开获取队列
              <AppIcon name="arrow-right" size={16} />
            </Link>
          </div>

          <div className="panel-card compact">
            <h2>快捷入口</h2>
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
              <h3>最近批次</h3>
              {recentBatches.length > 0 ? (
                recentBatches.slice(0, 3).map((batch) => <BatchRow batch={batch} key={batch.batch_id} />)
              ) : (
                <div className="queue-empty">当前还没有最近检索批次。</div>
              )}
            </div>
          </div>
        </section>
        <footer className="page-footer">基于本地论文库与毛玻璃研究工作台构建。</footer>
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
        <strong>{props.batch.title || props.batch.batch_id.replace(/-/g, " ")}</strong>
        <small>
          {props.batch.review_status} | {props.batch.candidate_total} 篇候选
        </small>
      </div>
      <em>{props.batch.keep_total} 保留</em>
    </div>
  );
}

function humanizeStage(stage: string): string {
  if (stage === "acquire") {
    return "获取中";
  }
  if (stage === "library") {
    return "已入库";
  }
  return stage || "未知";
}
