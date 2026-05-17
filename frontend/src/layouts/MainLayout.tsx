import { Outlet, useLocation } from "react-router-dom";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export function MainLayout() {
  const location = useLocation();
  const isLibraryWorkbench = location.pathname.startsWith("/papers");

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          {!isLibraryWorkbench ? <TopBar /> : null}
          <Outlet />
        </div>
      </div>
    </div>
  );
}
