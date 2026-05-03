import type { ReactNode } from "react";
import { JobNotifications } from "@/components/layout/JobNotifications";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  searchPlaceholder?: string;
  searchValue?: string;
  primaryActionIcon?: string;
  primaryActionLabel?: string;
  trailingContent?: ReactNode;
  onPrimaryAction?: () => void;
  onSearchChange?: (value: string) => void;
  onSearchSubmit?: () => void;
};

export function PageHeader({
  title,
  subtitle,
  searchPlaceholder,
  searchValue,
  primaryActionIcon,
  primaryActionLabel,
  trailingContent,
  onPrimaryAction,
  onSearchChange,
  onSearchSubmit,
}: PageHeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-outline-variant/10 bg-surface/90 px-6 py-5 backdrop-blur-xl sm:px-8">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <h1 className="text-xl font-extrabold tracking-tight text-on-surface">
            {title}
          </h1>
          {subtitle ? (
            <p className="mt-1 text-[10px] font-bold uppercase tracking-[0.24em] text-on-surface-variant">
              {subtitle}
            </p>
          ) : null}
        </div>

        <div className="flex flex-1 flex-col gap-3 xl:ml-6 xl:max-w-2xl xl:flex-row xl:items-center xl:justify-end">
          {searchPlaceholder ? (
            <div className="relative min-w-0 flex-1">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-base text-on-surface-variant">
                search
              </span>
              <input
                className="w-full rounded-lg border-none bg-surface-container-high py-2 pl-10 pr-4 text-sm outline-none transition-all focus:ring-2 focus:ring-primary/20"
                id={`${title.toLowerCase().replace(/\s+/g, "-")}-search`}
                name="page-search"
                onChange={(event) => onSearchChange?.(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    onSearchSubmit?.();
                  }
                }}
                placeholder={searchPlaceholder}
                type="text"
                value={searchValue}
              />
            </div>
          ) : null}

          <div className="flex items-center gap-3 self-start xl:self-auto">
            <JobNotifications />

            {trailingContent}

            {primaryActionLabel ? (
              <button
                className="flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-on-primary shadow-sm transition-all hover:bg-primary-dim"
                onClick={onPrimaryAction}
                type="button"
              >
                {primaryActionIcon ? (
                  <span className="material-symbols-outlined text-lg">
                    {primaryActionIcon}
                  </span>
                ) : null}
                <span>{primaryActionLabel}</span>
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
