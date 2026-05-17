import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type PageShellProps = {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function PageShell({ actions, children, className, description, title }: PageShellProps) {
  return (
    <main className={cn("mx-auto flex w-full max-w-[1440px] flex-1 flex-col gap-4 px-4 py-4 lg:px-6", className)}>
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-normal text-foreground">{title}</h1>
          {description ? <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p> : null}
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
      </header>
      {children}
    </main>
  );
}
