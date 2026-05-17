import type { ReactNode } from "react";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

type DisabledReasonTooltipProps = {
  children: ReactNode;
  reason?: string;
};

export function DisabledReasonTooltip({ children, reason }: DisabledReasonTooltipProps) {
  if (!reason) {
    return <>{children}</>;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex cursor-not-allowed">{children}</span>
        </TooltipTrigger>
        <TooltipContent className="max-w-64 leading-5">{reason}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
