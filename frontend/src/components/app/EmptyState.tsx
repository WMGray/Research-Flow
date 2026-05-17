import type { LucideIcon } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  className?: string;
};

export function EmptyState({ className, description, icon: Icon, title }: EmptyStateProps) {
  return (
    <Card className={cn("grid min-h-44 place-items-center p-6 text-center", className)}>
      <div className="max-w-sm">
        <div className="mx-auto grid h-9 w-9 place-items-center rounded-md border bg-muted text-muted-foreground">
          <Icon className="h-4 w-4" />
        </div>
        <h2 className="mt-3 text-sm font-semibold">{title}</h2>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
    </Card>
  );
}
