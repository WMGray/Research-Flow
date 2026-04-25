import type { ReactNode } from "react";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  searchPlaceholder?: string;
  primaryActionIcon?: string;
  primaryActionLabel?: string;
  trailingContent?: ReactNode;
};

export function PageHeader({
  title,
  subtitle,
  searchPlaceholder,
  primaryActionIcon,
  primaryActionLabel,
  trailingContent,
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
                placeholder={searchPlaceholder}
                type="text"
              />
            </div>
          ) : null}

          <div className="flex items-center gap-3 self-start xl:self-auto">
            <button
              className="flex h-10 w-10 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-primary"
              type="button"
            >
              <span className="material-symbols-outlined">notifications</span>
            </button>

            {trailingContent}

            {primaryActionLabel ? (
              <button
                className="flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-on-primary shadow-sm transition-all hover:bg-primary-dim"
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
