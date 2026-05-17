import type { ReactNode } from "react";
import { X } from "lucide-react";

import { DisabledReasonTooltip } from "@/components/common/DisabledReasonTooltip";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type BatchAction = {
  id: string;
  label: string;
  icon?: ReactNode;
  variant?: "default" | "outline" | "destructive" | "secondary" | "ghost";
  disabledReason?: string;
  onClick: () => void;
};

type BatchActionBarProps = {
  count: number;
  actions: BatchAction[];
  className?: string;
  onClear: () => void;
};

export function BatchActionBar({ actions, className, count, onClear }: BatchActionBarProps) {
  if (count === 0) {
    return null;
  }

  return (
    <div className={cn("sticky top-16 z-20 flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-card px-3 py-2 shadow-sm", className)}>
      <div className="flex items-center gap-2 text-sm">
        <span className="font-medium">已选择 {count} 项</span>
        <Button className="h-7 px-2" size="sm" variant="ghost" onClick={onClear}>
          <X className="h-3.5 w-3.5" />
          清空
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {actions.map((action) => {
          const button = (
            <Button key={action.id} size="sm" variant={action.variant ?? "outline"} disabled={Boolean(action.disabledReason)} onClick={action.onClick}>
              {action.icon}
              {action.label}
            </Button>
          );
          return action.disabledReason ? (
            <DisabledReasonTooltip key={action.id} reason={action.disabledReason}>
              {button}
            </DisabledReasonTooltip>
          ) : button;
        })}
      </div>
    </div>
  );
}
