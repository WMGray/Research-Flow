import { NavLink } from "react-router-dom";
import { AppIcon, type AppIconName } from "@/components/ui/AppIcon";

const items = [
  { to: "/", label: "Home", icon: "home" },
  { to: "/discover", label: "Discover", icon: "search" },
  { to: "/acquire", label: "Acquire", icon: "download" },
  { to: "/library", label: "Library", icon: "book" },
  { to: "/runtime", label: "Runtime", icon: "clock" },
  { to: "/logs", label: "Logs", icon: "document" },
] as const satisfies ReadonlyArray<{
  to: string;
  label: string;
  icon: AppIconName;
}>;

const utilityItems = [
  { label: "Settings", icon: "settings" },
  { label: "Help", icon: "help" },
] as const satisfies ReadonlyArray<{
  label: string;
  icon: AppIconName;
}>;

export function Sidebar() {
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
          >
            <AppIcon name={item.icon} size={18} />
          </button>
        ))}
        <div className="sidebar-avatar" title="Workspace owner">
          WG
        </div>
      </div>
    </aside>
  );
}
