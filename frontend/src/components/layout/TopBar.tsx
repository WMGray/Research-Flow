import { AppIcon } from "@/components/ui/AppIcon";
import { showPlaceholderAction } from "@/lib/placeholder";

type TopBarProps = {
  title: string;
  section?: string;
  current?: string;
};

export function TopBar({ title, section = "研究工作台", current }: TopBarProps) {
  const currentLabel = current ?? title;

  return (
    <header className="topbar">
      <div className="topbar-breadcrumb">
        <span className="topbar-title">{title}</span>
        <div className="topbar-current-group">
          <span className="topbar-section">{section}</span>
          <span className="topbar-arrow">&gt;</span>
          <span className="topbar-current">{currentLabel}</span>
        </div>
      </div>
      <div className="topbar-actions">
        <button aria-label="搜索" className="icon-button" type="button" onClick={() => showPlaceholderAction("搜索")}>
          <AppIcon name="search" size={18} />
        </button>
        <button aria-label="日程" className="icon-button" type="button" onClick={() => showPlaceholderAction("日程")}>
          <AppIcon name="calendar" size={18} />
        </button>
        <span className="topbar-divider" />
        <button aria-label="主题" className="icon-button" type="button" onClick={() => showPlaceholderAction("主题")}>
          <AppIcon name="sun" size={18} />
        </button>
      </div>
    </header>
  );
}
