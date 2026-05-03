import React from "react";

export function MetricCard({
  children,
  icon,
  label,
  loading,
  primary,
  secondary,
}: {
  children: React.ReactNode;
  icon: string;
  label: string;
  loading: boolean;
  primary: string;
  secondary: string;
}): React.ReactElement {
  return (
    <article className="rounded-[1.75rem] border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-on-surface-variant">
            {label}
          </p>
          <p className="mt-2 text-4xl font-black tracking-tight text-on-background">
            {loading ? "..." : primary}
          </p>
        </div>
        <div className="rounded-2xl bg-primary/10 p-2 text-primary">
          <span className="material-symbols-outlined">{icon}</span>
        </div>
      </div>
      <p className="mb-5 min-h-5 text-xs font-medium text-on-surface-variant">
        {secondary}
      </p>
      <div className="space-y-3">{children}</div>
    </article>
  );
}

export function ProgressRow({
  label,
  tone,
  value,
  width,
}: {
  label: string;
  tone: "primary" | "amber" | "gray";
  value: number;
  width: string;
}): React.ReactElement {
  const color =
    tone === "primary" ? "bg-primary" : tone === "amber" ? "bg-amber-400" : "bg-outline-variant";
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="w-24 text-xs text-on-surface-variant">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-container-high">
        <div className={`h-full ${color}`} style={{ width }} />
      </div>
      <span className="w-8 text-right text-xs font-bold text-on-surface">{value}</span>
    </div>
  );
}

export function MiniList({
  emptyLabel,
  items,
}: {
  emptyLabel: string;
  items: Array<{ key: string; title: string; detail: string }>;
}): React.ReactElement {
  if (items.length === 0) {
    return <EmptyState label={emptyLabel} />;
  }
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div className="min-w-0" key={item.key}>
          <p className="truncate text-xs font-bold text-on-surface">{item.title}</p>
          <p className="truncate text-[11px] text-on-surface-variant">{item.detail}</p>
        </div>
      ))}
    </div>
  );
}

export function Panel({
  children,
  icon,
  title,
}: {
  children: React.ReactNode;
  icon: string;
  title: string;
}): React.ReactElement {
  return (
    <section className="rounded-[1.75rem] border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
      <div className="mb-5 flex items-center gap-2">
        <span className="material-symbols-outlined text-lg text-primary">{icon}</span>
        <h2 className="text-xs font-black uppercase tracking-[0.18em] text-on-surface-variant">
          {title}
        </h2>
      </div>
      {children}
    </section>
  );
}

export function StatusPill({
  label,
  tone = "muted",
}: {
  label: string;
  tone?: "muted" | "success" | "warning";
}): React.ReactElement {
  const className =
    tone === "success"
      ? "bg-emerald-50 text-emerald-700 border-emerald-100"
      : tone === "warning"
        ? "bg-amber-50 text-amber-700 border-amber-100"
        : "bg-surface-container-high text-on-surface-variant border-outline-variant/20";
  return (
    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold ${className}`}>
      {label}
    </span>
  );
}

export function EmptyState({ label }: { label: string }): React.ReactElement {
  return (
    <div className="rounded-2xl border border-dashed border-outline-variant/30 bg-surface-container-low/30 px-4 py-3 text-xs font-medium text-on-surface-variant">
      {label}
    </div>
  );
}
