import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";

export function MainLayout() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-content">
        <Outlet />
      </div>
    </div>
  );
}

