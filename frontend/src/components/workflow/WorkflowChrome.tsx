import { AppIcon, type AppIconName } from "@/components/ui/AppIcon";

export type WorkflowView = "search" | "acquire";

export function WorkflowTabs(props: {
  currentView: WorkflowView;
  onChange: (nextView: WorkflowView) => void;
}) {
  return (
    <div className="workflow-tabs workflow-tabbar workflow-tabbar-dual">
      <button className={props.currentView === "search" ? "active" : ""} type="button" onClick={() => props.onChange("search")}>
        检索筛选
      </button>
      <button className={props.currentView === "acquire" ? "active" : ""} type="button" onClick={() => props.onChange("acquire")}>
        获取入库
      </button>
    </div>
  );
}

export function WorkflowHero(props: { view: WorkflowView }) {
  const isSearch = props.view === "search";

  return (
    <section className={`workflow-hero ${isSearch ? "search-hero" : "acquire-hero"}`}>
      <div className="workflow-hero-icon">
        <AppIcon name={isSearch ? "search" : "download"} size={40} />
      </div>
      <div className="workflow-hero-copy">
        <h1>{isSearch ? "更快找到值得跟进的论文" : "集中推进论文获取与入库"}</h1>
        <p>
          {isSearch
            ? "统一查看检索批次、候选质量和 Gate 1 决策，把真正值得继续投入的论文推进到获取队列。"
            : "统一处理手动入库、PDF 获取、解析状态和人工审核，把保留论文稳定推进到库内。"}
        </p>
      </div>
      <div className="workflow-hero-art" aria-hidden="true">
        <div className="workflow-art-disc" />
        <div className="workflow-art-card workflow-art-card-a" />
        <div className="workflow-art-card workflow-art-card-b" />
        <div className="workflow-art-card workflow-art-card-c" />
      </div>
    </section>
  );
}

export function WorkflowMetricCard(props: {
  icon: AppIconName;
  label: string;
  value: number;
  note: string;
}) {
  return (
    <div className="metric-card">
      <span className="stat-tile-icon">
        <AppIcon name={props.icon} size={18} />
      </span>
      <div>
        <span>{props.label}</span>
        <strong>{props.value}</strong>
        <small>{props.note}</small>
      </div>
    </div>
  );
}

export function Progress({ value }: { value: number }) {
  const safeValue = Math.max(0, Math.min(100, value));

  return (
    <span className="progress-cell">
      <em>{safeValue}%</em>
      <i>
        <b style={{ width: `${safeValue}%` }} />
      </i>
    </span>
  );
}
