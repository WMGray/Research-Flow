import React from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";

export const MainLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-surface">
      <Sidebar />
      <div className="min-h-screen min-w-0 pb-20 md:ml-64 md:pb-0">
        <Outlet />
      </div>
    </div>
  );
};
