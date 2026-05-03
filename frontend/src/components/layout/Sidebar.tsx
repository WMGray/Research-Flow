import React from "react";
import { NavLink } from "react-router-dom";

type NavItem = {
  icon: string;
  label: string;
  path: string;
};

const navItems: NavItem[] = [
  { icon: "dashboard", label: "Dashboard", path: "/" },
  { icon: "calendar_today", label: "Daily", path: "/daily" },
  { icon: "event", label: "Conferences", path: "/conferences" },
  { icon: "database", label: "Datasets", path: "/datasets" },
  { icon: "hub", label: "Discovery", path: "/discovery" },
  { icon: "library_books", label: "Library", path: "/library" },
  { icon: "folder_open", label: "Projects", path: "/projects" },
  { icon: "settings", label: "Settings", path: "/settings" },
  { icon: "visibility", label: "Views", path: "/views" },
];

function desktopLinkClass(isActive: boolean): string {
  if (isActive) {
    return "flex items-center gap-3 rounded-2xl bg-primary/10 px-4 py-3 font-semibold text-primary shadow-sm transition-colors";
  }

  return "flex items-center gap-3 rounded-2xl px-4 py-3 text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface";
}

function mobileLinkClass(isActive: boolean): string {
  if (isActive) {
    return "flex min-w-[72px] shrink-0 flex-col items-center justify-center gap-1 rounded-xl bg-primary/10 px-2 py-2 text-primary";
  }

  return "flex min-w-[72px] shrink-0 flex-col items-center justify-center gap-1 rounded-xl px-2 py-2 text-on-surface-variant";
}

export const Sidebar: React.FC = () => {
  return (
    <>
      <nav className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-outline-variant/10 bg-surface-container-lowest md:flex">
        <div className="px-6 pb-6 pt-8">
          <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-on-surface-variant">
            Research
          </p>
          <h2 className="mt-2 text-2xl font-black tracking-tight text-primary">
            Research-Flow
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-on-surface-variant">
            A focused workspace for reading, synthesis, and submission planning.
          </p>
        </div>

        <div className="flex-1 space-y-1 px-3">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              className={({ isActive }) => desktopLinkClass(isActive)}
              end={item.path === "/"}
              to={item.path}
            >
              <span className="material-symbols-outlined text-[20px]">
                {item.icon}
              </span>
              <span className="truncate text-sm font-medium tracking-tight">
                {item.label}
              </span>
            </NavLink>
          ))}
        </div>

        <div className="border-t border-outline-variant/10 px-4 pb-5 pt-4">
          <div className="rounded-3xl bg-surface-container-low p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-on-surface-variant">
              Active Focus
            </p>
            <p className="mt-3 text-sm font-semibold text-on-surface">
              Submission pacing
            </p>
            <p className="mt-1 text-sm leading-relaxed text-on-surface-variant">
              Tighten project structure, linked papers, and view extraction
              before the next draft cycle.
            </p>
          </div>
        </div>
      </nav>

      <nav className="fixed inset-x-0 bottom-0 z-50 flex items-center gap-1 overflow-x-auto border-t border-outline-variant/10 bg-surface-container-lowest/95 px-2 py-2 backdrop-blur md:hidden">
        {navItems.map((item) => {
          return (
            <NavLink
              key={item.path}
              className={({ isActive }) => mobileLinkClass(isActive)}
              end={item.path === "/"}
              to={item.path}
            >
              <span className="material-symbols-outlined text-[18px]">
                {item.icon}
              </span>
              <span className="truncate text-[10px] font-semibold tracking-tight">
                {item.label}
              </span>
            </NavLink>
          );
        })}
      </nav>
    </>
  );
};
