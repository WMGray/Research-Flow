import { NavLink, useNavigate } from "react-router-dom";
import { AppIcon, type AppIconName } from "@/components/ui/AppIcon";
import { showPlaceholderAction } from "@/lib/placeholder";

const items = [
  { to: "/", label: "首页", icon: "home" },
  { to: "/discover", label: "Workflow", icon: "search" },
  { to: "/config", label: "配置", icon: "settings" },
] as const satisfies ReadonlyArray<{
  to: string;
  label: string;
  icon: AppIconName;
}>;

const utilityItems = [
  { label: "设置", icon: "settings", to: "/config" },
  { label: "帮助", icon: "help" },
] as const satisfies ReadonlyArray<{
  label: string;
  icon: AppIconName;
  to?: string;
}>;

export function Sidebar() {
  const navigate = useNavigate();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-gem" />
      </div>
      <nav className="sidebar-nav">
        {items.map((item) => (
          <NavLink
            aria-label={item.label}
            key={item.to}
            title={item.label}
            to={item.to}
            className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
          >
            <span className="sidebar-icon">
              <AppIcon name={item.icon} size={20} />
            </span>
            <span className="sidebar-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        {utilityItems.map((item) => (
          <button
            aria-label={item.label}
            className="sidebar-utility"
            key={item.label}
            title={item.label}
            type="button"
            onClick={() => {
              if ("to" in item && item.to) {
                navigate(item.to);
                return;
              }
              showPlaceholderAction(item.label);
            }}
          >
            <AppIcon name={item.icon} size={18} />
          </button>
        ))}
        <div className="sidebar-avatar" title="工作区所有者">
          WG
        </div>
      </div>
    </aside>
  );
}
