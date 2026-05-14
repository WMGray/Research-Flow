import { AppIcon } from "@/components/ui/AppIcon";

type TopBarProps = {
  title: string;
  section?: string;
  current?: string;
};

export function TopBar({
  title,
  section = "Research Workspace",
  current,
}: TopBarProps) {
  const currentLabel = current ?? title;

  return (
    <header className="topbar">
      <div className="topbar-breadcrumb">
        <span className="topbar-title">{title}</span>
        <div className="topbar-current-group">
          <span className="topbar-section">{section}</span>
          <span className="topbar-arrow">›</span>
          <span className="topbar-current">{currentLabel}</span>
        </div>
      </div>
      <div className="topbar-actions">
        <button aria-label="Search" className="icon-button" type="button">
          <AppIcon name="search" size={18} />
        </button>
        <button aria-label="Calendar" className="icon-button" type="button">
          <AppIcon name="calendar" size={18} />
        </button>
        <span className="topbar-divider" />
        <button aria-label="Theme" className="icon-button" type="button">
          <AppIcon name="sun" size={18} />
        </button>
      </div>
    </header>
  );
}
