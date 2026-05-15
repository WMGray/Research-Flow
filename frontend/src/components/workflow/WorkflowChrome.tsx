import { Link } from "react-router-dom";
import { AppIcon, type AppIconName } from "@/components/ui/AppIcon";

export type WorkflowView = "search" | "acquire";

export function WorkflowTabs(props: {
  currentView: WorkflowView;
  onChange: (nextView: WorkflowView) => void;
}) {
  return (
    <div className="workflow-tabs workflow-tabbar">
      <button className={props.currentView === "search" ? "active" : ""} type="button" onClick={() => props.onChange("search")}>
        Search
      </button>
      <button className={props.currentView === "acquire" ? "active" : ""} type="button" onClick={() => props.onChange("acquire")}>
        Acquire
      </button>
      <Link className="workflow-tab-link" to="/library">
        Library
      </Link>
    </div>
  );
}

export function WorkflowHero(props: { view: WorkflowView }) {
  const isSearch = props.view === "search";

  return (
    <section className={`workflow-hero ${isSearch ? "search-hero" : "acquire-hero"}`}>
      <div className="workflow-hero-main">
        <div className="workflow-hero-icon">
          <AppIcon name={isSearch ? "search" : "download"} size={40} />
        </div>
        <div className="workflow-hero-copy">
          <span className="workflow-hero-kicker">{isSearch ? "Discovery Workflow" : "Acquire Workflow"}</span>
          <h1>{isSearch ? "Focus on the papers worth keeping" : "Accelerate paper acquisition"}</h1>
          <p>
            {isSearch
              ? "Review search batches, AI scores, and recommendation reasons in one place before promoting papers into the acquire queue."
              : "Track curated papers, acquire full texts, and move them through parsing, review, and confirmation with visible stage status."}
          </p>
        </div>
      </div>
      <div className="workflow-hero-art" aria-hidden="true">
        <div className="workflow-art-grid" />
        <div className="workflow-art-stack">
          <span className="workflow-art-stack-card stack-card-a" />
          <span className="workflow-art-stack-card stack-card-b" />
          <span className="workflow-art-stack-card stack-card-c" />
          <span className="workflow-art-stack-card stack-card-d" />
        </div>
        <div className="workflow-art-cloud" />
        <div className="workflow-art-server" />
        <div className="workflow-art-cube cube-a" />
        <div className="workflow-art-cube cube-b" />
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
      <span>{props.label}</span>
      <strong>{props.value}</strong>
      <small>{props.note}</small>
    </div>
  );
}
