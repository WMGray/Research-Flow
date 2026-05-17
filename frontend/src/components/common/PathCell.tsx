import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { middleEllipsis } from "@/lib/format";
import { cn } from "@/lib/utils";

type PathCellProps = {
  value: string;
  emptyText?: string;
  className?: string;
};

export function PathCell({ className, emptyText = "未填写", value }: PathCellProps) {
  const [copied, setCopied] = useState(false);

  if (!value) {
    return <span className={cn("text-muted-foreground", className)}>{emptyText}</span>;
  }

  const copy = async () => {
    try {
      await navigator.clipboard?.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className={cn("flex min-w-0 items-center gap-1.5", className)}>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="min-w-0 truncate text-xs text-muted-foreground">{middleEllipsis(value)}</span>
          </TooltipTrigger>
          <TooltipContent className="max-w-[420px] break-all leading-5">{value}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <Button className="h-6 w-6 shrink-0" size="icon" variant="ghost" onClick={copy}>
        {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
        <span className="sr-only">复制路径</span>
      </Button>
    </div>
  );
}
