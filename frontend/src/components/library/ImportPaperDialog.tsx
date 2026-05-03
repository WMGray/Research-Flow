import type { CategoryRecord, PaperResolveMode } from "@/lib/api";

const importModes: Array<{
  value: PaperResolveMode;
  label: string;
  placeholder: string;
}> = [
  {
    value: "source_url",
    label: "URL",
    placeholder: "https://arxiv.org/abs/1706.03762",
  },
  {
    value: "doi",
    label: "DOI",
    placeholder: "10.48550/arXiv.1706.03762",
  },
  {
    value: "title",
    label: "Title",
    placeholder: "Attention Is All You Need",
  },
];

type ImportPaperDialogProps = {
  categories: CategoryRecord[];
  categoryId: number | null;
  error: string | null;
  isOpen: boolean;
  isSubmitting: boolean;
  mode: PaperResolveMode;
  value: string;
  onCategoryChange: (categoryId: number | null) => void;
  onClose: () => void;
  onModeChange: (mode: PaperResolveMode) => void;
  onSubmit: () => void;
  onValueChange: (value: string) => void;
};

export function ImportPaperDialog({
  categories,
  categoryId,
  error,
  isOpen,
  isSubmitting,
  mode,
  value,
  onCategoryChange,
  onClose,
  onModeChange,
  onSubmit,
  onValueChange,
}: ImportPaperDialogProps) {
  if (!isOpen) {
    return null;
  }

  const activeMode = importModes.find((item) => item.value === mode) ?? importModes[0];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-on-background/35 px-4 py-8 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-lg bg-surface-container-lowest p-6 shadow-[0_24px_80px_rgba(22,32,34,0.24)]">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-extrabold text-on-surface">Import Paper</h2>
            <p className="mt-1 text-sm text-on-surface-variant">
              Resolve metadata from one input, then start PDF download.
            </p>
          </div>
          <button
            className="flex h-9 w-9 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-surface-container"
            onClick={onClose}
            type="button"
          >
            <span className="material-symbols-outlined text-xl">close</span>
          </button>
        </div>

        <div className="mb-4 grid grid-cols-3 rounded-lg bg-surface-container p-1">
          {importModes.map((item) => (
            <button
              className={`rounded-md px-3 py-2 text-sm font-bold transition-colors ${
                item.value === mode
                  ? "bg-surface-container-lowest text-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
              key={item.value}
              onClick={() => onModeChange(item.value)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>

        <label
          className="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-on-surface-variant"
          htmlFor="paper-import-input"
        >
          {activeMode.label}
        </label>
        <input
          autoFocus
          className="w-full rounded-lg border border-outline-variant/40 bg-surface-container-lowest px-3 py-3 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
          id="paper-import-input"
          name="paper-import-input"
          onChange={(event) => onValueChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && value.trim() && !isSubmitting) {
              onSubmit();
            }
          }}
          placeholder={activeMode.placeholder}
          type="text"
          value={value}
        />

        <label
          className="mb-2 mt-4 block text-xs font-bold uppercase tracking-[0.18em] text-on-surface-variant"
          htmlFor="paper-import-domain"
        >
          Domain
        </label>
        <select
          className="w-full rounded-lg border border-outline-variant/40 bg-surface-container-lowest px-3 py-3 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
          id="paper-import-domain"
          name="paper-import-domain"
          onChange={(event) => {
            const nextValue = event.target.value;
            onCategoryChange(nextValue ? Number(nextValue) : null);
          }}
          value={categoryId ?? ""}
        >
          <option value="">No domain</option>
          {flattenCategories(categories).map((category) => (
            <option key={category.category_id} value={category.category_id}>
              {category.label}
            </option>
          ))}
        </select>

        <div className="mt-4 flex gap-3 rounded-lg bg-primary/5 p-3 text-sm text-on-surface-variant">
          <span className="material-symbols-outlined mt-0.5 text-lg text-primary">
            fact_check
          </span>
          <p>
            The pipeline stops after refined parsing so you can review the
            refined document before confirming downstream section, note,
            knowledge, and dataset generation.
          </p>
        </div>

        {error ? (
          <div className="mt-4 rounded-lg border border-error/20 bg-red-50 px-3 py-2 text-sm font-medium text-error">
            {error}
          </div>
        ) : null}

        <div className="mt-6 flex justify-end gap-3">
          <button
            className="h-10 rounded-lg px-4 text-sm font-semibold text-on-surface-variant transition-colors hover:bg-surface-container"
            onClick={onClose}
            type="button"
          >
            Cancel
          </button>
          <button
            className="flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-on-primary shadow-sm transition-all disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!value.trim() || isSubmitting}
            onClick={onSubmit}
            type="button"
          >
            <span className="material-symbols-outlined text-lg">
              {isSubmitting ? "progress_activity" : "download"}
            </span>
            <span>{isSubmitting ? "Importing..." : "Resolve & Download"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

function flattenCategories(
  categories: CategoryRecord[],
  depth = 0,
): Array<CategoryRecord & { label: string }> {
  return categories.flatMap((category) => [
    {
      ...category,
      label: `${"  ".repeat(depth)}${depth > 0 ? "- " : ""}${category.name}`,
    },
    ...flattenCategories(category.children ?? [], depth + 1),
  ]);
}
