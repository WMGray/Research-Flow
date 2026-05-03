type StatusFilterProps = {
  active?: boolean;
  count: number;
  icon: string;
  label: string;
  onClick?: () => void;
};

export function StatusFilter({
  active = false,
  count,
  icon,
  label,
  onClick,
}: StatusFilterProps) {
  return (
    <button
      className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left transition-colors ${
        active
          ? "bg-surface-container-highest text-primary"
          : "text-on-surface-variant hover:bg-surface-container"
      }`}
      onClick={onClick}
      type="button"
    >
      <span className="flex min-w-0 items-center gap-2">
        <span className="material-symbols-outlined text-lg">{icon}</span>
        <span className="truncate text-sm font-semibold">{label}</span>
      </span>
      <span className="text-xs font-bold">{count}</span>
    </button>
  );
}
