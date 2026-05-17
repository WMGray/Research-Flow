import { Badge } from "@/components/ui/badge";
import { humanizeStatus, statusTone } from "@/lib/format";
import { cn } from "@/lib/utils";

type StatusBadgeProps = {
  status: string;
  className?: string;
  dot?: boolean;
};

export function StatusBadge({ className, dot = true, status }: StatusBadgeProps) {
  const tone = statusTone(status);

  return (
    <Badge className={cn("gap-1.5", className)} variant={tone}>
      {dot ? <span className={cn("h-1.5 w-1.5 rounded-full", dotClassName(tone))} /> : null}
      {humanizeStatus(status)}
    </Badge>
  );
}

function dotClassName(tone: ReturnType<typeof statusTone>): string {
  switch (tone) {
    case "success":
      return "bg-emerald-500";
    case "info":
      return "bg-blue-500";
    case "warning":
      return "bg-amber-500";
    case "danger":
      return "bg-red-500";
    default:
      return "bg-muted-foreground";
  }
}
