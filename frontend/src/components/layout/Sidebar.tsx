import { BookOpen, Search, Settings } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/papers", label: "Papers", icon: BookOpen },
  { to: "/discover", label: "搜索", icon: Search },
  { to: "/settings", label: "设置", icon: Settings },
] as const;

export function Sidebar() {
  return (
    <aside className="hidden h-screen w-14 shrink-0 border-r bg-white lg:sticky lg:top-0 lg:flex lg:flex-col lg:items-center">
      <div className="grid h-14 w-full place-items-center border-b">
        <div className="grid h-8 w-8 place-items-center rounded border bg-slate-50 text-[12px] font-semibold text-slate-700" aria-label="Research Flow">
          RF
        </div>
      </div>

      <TooltipProvider>
        <nav className="flex flex-1 flex-col items-center gap-1 py-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Tooltip key={item.to}>
                <TooltipTrigger asChild>
                  <NavLink
                    aria-label={item.label}
                    className={({ isActive }) =>
                      cn(
                        "grid h-10 w-10 place-items-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900",
                        isActive && "bg-slate-100 text-slate-900",
                      )
                    }
                    to={item.to}
                  >
                    <Icon className="h-4 w-4" />
                  </NavLink>
                </TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            );
          })}
        </nav>
      </TooltipProvider>
    </aside>
  );
}
