import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ImportPaperDialog } from "@/components/library/ImportPaperDialog";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  APIError,
  createCategory,
  confirmPaperReview,
  deleteCategory,
  importPaper,
  listCategories,
  listPapers,
  paperNoteUrl,
  paperPdfUrl,
  retryPaperPipeline,
  updatePaper,
  type CategoryRecord,
  type PaperResolveMode,
  type PaperRecord,
} from "@/lib/api";

type PaperCardProps = {
  categories: CategoryRecord[];
  categoryName: string;
  paper: PaperRecord;
  isAdvancing: boolean;
  isAssigningDomain: boolean;
  isFocused: boolean;
  isRetrying: boolean;
  paperRef?: React.RefObject<HTMLDivElement | null>;
  onAssignDomain: (paper: PaperRecord, categoryId: number | null) => void;
  onRetryPipeline: (paper: PaperRecord) => void;
  onReviewConfirm: (paper: PaperRecord) => void;
};

const PAPER_PAGE_SIZE = 20;
const PAPER_POLL_INTERVAL_MS = 3000;
const LIVE_STATUSES = new Set(["queued", "running"]);
const PAPER_SORT_OPTIONS = [
  { label: "Updated", value: "updated_at" },
  { label: "Created", value: "created_at" },
  { label: "Year", value: "year" },
  { label: "Title", value: "title" },
] as const;

const statusLabels: Record<string, string> = {
  metadata_ready: "Metadata",
  downloaded: "Downloaded",
  parsed: "Parsed",
  refined: "Refined",
  review_confirmed: "Reviewed",
  sectioned: "Sectioned",
  noted: "Noted",
  knowledge_extracted: "Knowledge",
  dataset_extracted: "Datasets",
  completed: "Completed",
  error: "Error",
};

const jobTypeLabels: Record<string, string> = {
  paper_resolve_metadata: "Metadata",
  paper_download: "Download",
  paper_parse: "Parse",
  paper_refine_parse: "Refine",
  paper_split_sections: "Sections",
  paper_generate_note: "Note",
  paper_extract_knowledge: "Knowledge",
  paper_extract_datasets: "Datasets",
};

const jobStatusLabels: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  waiting_review: "Waiting Review",
  waiting_confirm: "Waiting Confirm",
  succeeded: "Succeeded",
  failed: "Failed",
  cancelled: "Cancelled",
};

export const LibraryPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [papers, setPapers] = useState<PaperRecord[]>([]);
  const [categories, setCategories] = useState<CategoryRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [libraryTotal, setLibraryTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [draftQuery, setDraftQuery] = useState("");
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [selectedStage, setSelectedStage] = useState<string>("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [sort, setSort] = useState<(typeof PAPER_SORT_OPTIONS)[number]["value"]>(
    "updated_at",
  );
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [importMode, setImportMode] = useState<PaperResolveMode>("source_url");
  const [importValue, setImportValue] = useState("");
  const [importCategoryId, setImportCategoryId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [isDomainOpen, setIsDomainOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isCreatingDomain, setIsCreatingDomain] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [advancingPaperId, setAdvancingPaperId] = useState<number | null>(null);
  const [assigningPaperId, setAssigningPaperId] = useState<number | null>(null);
  const [deletingDomainId, setDeletingDomainId] = useState<number | null>(null);
  const [retryingPaperId, setRetryingPaperId] = useState<number | null>(null);
  const [domainName, setDomainName] = useState("");
  const [domainParentId, setDomainParentId] = useState<number | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [domainError, setDomainError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const focusedPaperId = Number.parseInt(searchParams.get("paper_id") ?? "", 10);
  const focusedPaperRef = useRef<HTMLDivElement | null>(null);

  const loadPapers = useCallback(
    async ({
      signal,
      showLoading = false,
      showRefreshing = false,
      categoryIdOverride,
      queryOverride,
      pageOverride,
      paperStageOverride,
      sortOverride,
      orderOverride,
      yearFromOverride,
      yearToOverride,
    }: {
      signal?: AbortSignal;
      showLoading?: boolean;
      showRefreshing?: boolean;
      categoryIdOverride?: number | null;
      queryOverride?: string;
      pageOverride?: number;
      paperStageOverride?: string | null;
      sortOverride?: (typeof PAPER_SORT_OPTIONS)[number]["value"];
      orderOverride?: "asc" | "desc";
      yearFromOverride?: string;
      yearToOverride?: string;
    } = {}) => {
      if (showLoading) {
        setIsLoading(true);
      }
      if (showRefreshing) {
        setIsRefreshing(true);
      }
      setError(null);

      try {
        const result = await listPapers({
          q: queryOverride ?? query,
          categoryId:
            categoryIdOverride === undefined
              ? selectedCategoryId
              : categoryIdOverride,
          paperStage:
            paperStageOverride === undefined ? selectedStage : paperStageOverride,
          yearFrom: parseOptionalYear(yearFromOverride ?? yearFrom),
          yearTo: parseOptionalYear(yearToOverride ?? yearTo),
          sort: sortOverride ?? sort,
          order: orderOverride ?? order,
          page: pageOverride ?? page,
          pageSize: PAPER_PAGE_SIZE,
        }, signal);
        setPapers(result.papers);
        setTotal(result.total);
        setPage(result.page);
        setLastSyncedAt(new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }));
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        setError(formatError(err));
      } finally {
        if (showLoading) {
          setIsLoading(false);
        }
        if (showRefreshing) {
          setIsRefreshing(false);
        }
      }
    },
    [order, page, query, selectedCategoryId, selectedStage, sort, yearFrom, yearTo],
  );

  const loadCategories = useCallback(async (signal?: AbortSignal) => {
    try {
      const records = await listCategories();
      if (!signal?.aborted) {
        setCategories(records);
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      setError(formatError(err));
    }
  }, []);

  const loadLibraryTotal = useCallback(async (signal?: AbortSignal) => {
    try {
      const result = await listPapers({ page: 1, pageSize: 1 }, signal);
      if (!signal?.aborted) {
        setLibraryTotal(result.total);
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      setError(formatError(err));
    }
  }, []);

  const refreshLibrary = useCallback(
    async (
      options: Parameters<typeof loadPapers>[0] = {},
      signal?: AbortSignal,
    ) => {
      await Promise.all([
        loadPapers(options),
        loadCategories(signal),
        loadLibraryTotal(signal),
      ]);
    },
    [loadCategories, loadLibraryTotal, loadPapers],
  );

  useEffect(() => {
    const controller = new AbortController();
    void refreshLibrary(
      { signal: controller.signal, showLoading: true },
      controller.signal,
    );

    return () => {
      controller.abort();
    };
  }, [refreshLibrary]);

  const hasLivePaper = useMemo(() => {
    return papers.some((paper) =>
      [
        paper.latest_job_status,
        paper.download_status,
        paper.parse_status,
        paper.refine_status,
      ].some((status) => LIVE_STATUSES.has(status)),
    );
  }, [papers]);

  useEffect(() => {
    if (!hasLivePaper) {
      return;
    }
    const timer = window.setInterval(() => {
      void refreshLibrary({ showRefreshing: true });
    }, PAPER_POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [hasLivePaper, refreshLibrary]);

  useEffect(() => {
    function refreshWhenVisible(): void {
      if (document.visibilityState === "visible") {
        void refreshLibrary({ showRefreshing: true });
      }
    }

    window.addEventListener("focus", refreshWhenVisible);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.removeEventListener("focus", refreshWhenVisible);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [refreshLibrary]);

  useEffect(() => {
    if (Number.isNaN(focusedPaperId) || focusedPaperId <= 0) {
      return;
    }
    focusedPaperRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }, [focusedPaperId, papers]);

  const visibleStatusCounts = useMemo(() => {
    return papers.reduce<Record<string, number>>((counts, paper) => {
      counts[paper.paper_stage] = (counts[paper.paper_stage] ?? 0) + 1;
      return counts;
    }, {});
  }, [papers]);
  const hasActiveFilters = Boolean(
    query || selectedCategoryId || selectedStage || yearFrom || yearTo,
  );
  const totalPages = Math.max(1, Math.ceil(total / PAPER_PAGE_SIZE));

  const flatCategories = useMemo(() => flattenCategories(categories), [categories]);

  const categoryNames = useMemo(() => {
    return flatCategories.reduce<Record<number, string>>((names, category) => {
      names[category.category_id] = category.label.trim();
      return names;
    }, {});
  }, [flatCategories]);

  async function handleCreatePaper(): Promise<void> {
    const value = importValue.trim();
    if (!value) {
      return;
    }

    setIsCreating(true);
    setImportError(null);
    setError(null);
    try {
      const createdPaper = await importPaper({
        mode: importMode,
        value,
        categoryId: importCategoryId,
      });
      setDraftQuery("");
      setQuery("");
      setSelectedStage("");
      setPage(1);
      setPapers((currentPapers) => mergePaper(currentPapers, createdPaper));
      setTotal((currentTotal) =>
        papers.some((paper) => paper.paper_id === createdPaper.paper_id)
          ? currentTotal
          : currentTotal + 1,
      );
      setLastSyncedAt(new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }));
      setImportValue("");
      setImportCategoryId(selectedCategoryId);
      setIsImportOpen(false);
      void refreshLibrary({ showRefreshing: true });
    } catch (err) {
      setImportError(formatError(err));
    } finally {
      setIsCreating(false);
    }
  }

  async function handleCreateDomain(): Promise<void> {
    const name = domainName.trim();
    if (!name) {
      return;
    }

    setIsCreatingDomain(true);
    setDomainError(null);
    try {
      const createdDomain = await createCategory({
        name,
        parent_id: domainParentId,
      });
      setSelectedCategoryId(createdDomain.category_id);
      setPage(1);
      setDomainName("");
      setDomainParentId(null);
      setIsDomainOpen(false);
      await refreshLibrary({ showRefreshing: true });
    } catch (err) {
      setDomainError(formatError(err));
    } finally {
      setIsCreatingDomain(false);
    }
  }

  async function handleDeleteDomain(category: CategoryRecord): Promise<void> {
    setDeletingDomainId(category.category_id);
    setDomainError(null);
    setError(null);
    try {
      await deleteCategory(category.category_id);
      if (selectedCategoryId === category.category_id) {
        setSelectedCategoryId(null);
        setPage(1);
        await refreshLibrary({
          categoryIdOverride: null,
          pageOverride: 1,
          showRefreshing: true,
        });
        return;
      }
      await refreshLibrary({ showRefreshing: true });
    } catch (err) {
      setError(formatError(err));
    } finally {
      setDeletingDomainId(null);
    }
  }

  async function handleAssignDomain(
    paper: PaperRecord,
    categoryId: number | null,
  ): Promise<void> {
    setAssigningPaperId(paper.paper_id);
    setError(null);
    try {
      const updatedPaper = await updatePaper(paper.paper_id, {
        category_id: categoryId,
      });
      setPapers((currentPapers) => mergePaper(currentPapers, updatedPaper));
      await refreshLibrary({ showRefreshing: true });
    } catch (err) {
      setError(formatError(err));
    } finally {
      setAssigningPaperId(null);
    }
  }

  async function handleConfirmReview(paper: PaperRecord): Promise<void> {
    setAdvancingPaperId(paper.paper_id);
    setError(null);
    try {
      const result = await confirmPaperReview(paper.paper_id);
      setPapers((currentPapers) => mergePaper(currentPapers, result.paper));

      if (result.job.status === "failed") {
        throw new Error(result.job.error?.message ?? result.job.message);
      }
      await refreshLibrary({ showRefreshing: true });
    } catch (err) {
      setError(formatError(err));
    } finally {
      setAdvancingPaperId(null);
    }
  }

  async function handleRetryPipeline(paper: PaperRecord): Promise<void> {
    setRetryingPaperId(paper.paper_id);
    setError(null);
    try {
      const result = await retryPaperPipeline(paper.paper_id);
      setPapers((currentPapers) => mergePaper(currentPapers, result.paper));
      await refreshLibrary({ showRefreshing: true });
    } catch (err) {
      setError(formatError(err));
    } finally {
      setRetryingPaperId(null);
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        primaryActionIcon="add_circle"
        primaryActionLabel={isCreating ? "Adding..." : "Add Paper"}
        searchPlaceholder="Search papers, authors, or venues..."
        subtitle="Archive and note coverage"
        title="Library"
        onPrimaryAction={() => {
          setImportError(null);
          setImportCategoryId(selectedCategoryId);
          setIsImportOpen(true);
        }}
        onSearchChange={setDraftQuery}
        onSearchSubmit={() => {
          setQuery(draftQuery.trim());
          setPage(1);
        }}
        searchValue={draftQuery}
      />

      <main className="grid gap-8 p-6 sm:p-8 xl:grid-cols-[18rem_minmax(0,1fr)]">
        <section className="flex flex-col rounded-lg bg-surface-container-low p-6">
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-[0.22em] text-on-surface-variant">
                Domains
              </h3>
              <button
                aria-label="Create domain"
                className="flex h-8 w-8 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-surface-container hover:text-primary"
                onClick={() => {
                  setDomainError(null);
                  setDomainParentId(selectedCategoryId);
                  setIsDomainOpen(true);
                }}
                type="button"
              >
                <span className="material-symbols-outlined text-lg">add</span>
              </button>
            </div>
            <div className="space-y-1">
              {flatCategories.length > 0 ? (
                flatCategories.map((category) => (
                  <DomainFilter
                    active={selectedCategoryId === category.category_id}
                    count={category.paper_count}
                    disabled={deletingDomainId === category.category_id}
                    icon={category.depth === 0 ? "folder" : "subdirectory_arrow_right"}
                    key={category.category_id}
                    label={category.label}
                    onDelete={() => void handleDeleteDomain(category)}
                    onClick={() => {
                      setSelectedCategoryId(category.category_id);
                      setPage(1);
                    }}
                  />
                ))
              ) : (
                <div className="rounded-lg border border-dashed border-outline-variant/40 px-3 py-4 text-sm text-on-surface-variant">
                  Create a domain to organize papers before review.
                </div>
              )}
            </div>
          </div>

          <div className="mt-8 border-t border-outline-variant/10 pt-6">
            <div className="mb-6 flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-[0.22em] text-on-surface-variant">
                Collections
              </h3>
              <span className="material-symbols-outlined text-sm text-on-surface-variant">
                filter_list
              </span>
            </div>

            <div className="space-y-2">
              <StatusFilter
                active={query === "" && selectedCategoryId === null}
                count={libraryTotal}
                icon="library_books"
                label="All Papers"
                onClick={() => {
                  setDraftQuery("");
                  setQuery("");
                  setSelectedCategoryId(null);
                  setSelectedStage("");
                  setYearFrom("");
                  setYearTo("");
                  setPage(1);
                }}
              />
              {Object.entries(visibleStatusCounts).map(([stage, count]) => (
                <StatusFilter
                  active={selectedStage === stage}
                  key={stage}
                  count={count}
                  icon={stage === "completed" ? "check_circle" : "radio_button_unchecked"}
                  label={statusLabels[stage] ?? stage}
                  onClick={() => {
                    setSelectedStage((current) => (current === stage ? "" : stage));
                    setPage(1);
                  }}
                />
              ))}
            </div>
          </div>
        </section>

        <section className="flex min-w-0 flex-col">
          <div className="mb-4 flex flex-col gap-3 px-2 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm font-bold text-on-surface">
                {total} Papers
              </span>
              {isRefreshing ? (
                <span className="rounded-full bg-surface-container px-2 py-0.5 text-[10px] font-bold text-on-surface-variant">
                  Syncing
                </span>
              ) : lastSyncedAt ? (
                <span className="rounded-full bg-surface-container px-2 py-0.5 text-[10px] font-bold text-on-surface-variant">
                  Updated {lastSyncedAt}
                </span>
              ) : null}
              {query ? (
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">
                  Search: {query}
                </span>
              ) : null}
              {selectedCategoryId ? (
                <span className="rounded-full bg-secondary-container px-2 py-0.5 text-[10px] font-bold text-on-secondary-container">
                  Domain: {categoryNames[selectedCategoryId] ?? selectedCategoryId}
                </span>
              ) : null}
              {selectedStage ? (
                <FilterChip
                  label={`Stage: ${statusLabels[selectedStage] ?? selectedStage}`}
                  onClear={() => {
                    setSelectedStage("");
                    setPage(1);
                  }}
                />
              ) : null}
              {yearFrom || yearTo ? (
                <FilterChip
                  label={`Year: ${yearFrom || "min"}-${yearTo || "max"}`}
                  onClear={() => {
                    setYearFrom("");
                    setYearTo("");
                    setPage(1);
                  }}
                />
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label className="sr-only" htmlFor="library-year-from">
                Year from
              </label>
              <input
                className="h-9 w-24 rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 text-xs font-bold text-on-surface outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
                id="library-year-from"
                inputMode="numeric"
                maxLength={4}
                onChange={(event) => {
                  setYearFrom(event.target.value.replace(/\D/g, "").slice(0, 4));
                  setPage(1);
                }}
                placeholder="From"
                type="text"
                value={yearFrom}
              />
              <label className="sr-only" htmlFor="library-year-to">
                Year to
              </label>
              <input
                className="h-9 w-24 rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 text-xs font-bold text-on-surface outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
                id="library-year-to"
                inputMode="numeric"
                maxLength={4}
                onChange={(event) => {
                  setYearTo(event.target.value.replace(/\D/g, "").slice(0, 4));
                  setPage(1);
                }}
                placeholder="To"
                type="text"
                value={yearTo}
              />
              <label className="sr-only" htmlFor="library-sort">
                Sort papers
              </label>
              <select
                className="h-9 rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 text-xs font-bold text-on-surface outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
                id="library-sort"
                onChange={(event) => {
                  setSort(
                    event.target.value as (typeof PAPER_SORT_OPTIONS)[number]["value"],
                  );
                  setPage(1);
                }}
                value={sort}
              >
                {PAPER_SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <button
                aria-label="Toggle sort order"
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-outline-variant/30 bg-surface-container-lowest text-on-surface-variant transition-colors hover:bg-surface-container"
                onClick={() => {
                  setOrder((current) => (current === "desc" ? "asc" : "desc"));
                  setPage(1);
                }}
                title={order === "desc" ? "Descending" : "Ascending"}
                type="button"
              >
                <span className="material-symbols-outlined text-lg">
                  {order === "desc" ? "south" : "north"}
                </span>
              </button>
              {hasActiveFilters ? (
                <button
                  className="h-9 rounded-lg px-3 text-xs font-bold text-on-surface-variant transition-colors hover:bg-surface-container"
                  onClick={() => {
                    setDraftQuery("");
                    setQuery("");
                    setSelectedCategoryId(null);
                    setSelectedStage("");
                    setYearFrom("");
                    setYearTo("");
                    setPage(1);
                  }}
                  type="button"
                >
                  Clear
                </button>
              ) : null}
            </div>
          </div>

          {error ? (
            <div className="mb-4 rounded-lg border border-error/20 bg-red-50 px-4 py-3 text-sm font-medium text-error">
              {error}
            </div>
          ) : null}

          {isLoading ? (
            <PaperListSkeleton />
          ) : papers.length > 0 ? (
            <div className="space-y-3">
              {papers.map((paper) => (
                <PaperCard
                  categories={categories}
                  categoryName={
                    paper.category_id
                      ? categoryNames[paper.category_id] ?? "Unknown domain"
                      : "No domain"
                  }
                  isAdvancing={advancingPaperId === paper.paper_id}
                  isAssigningDomain={assigningPaperId === paper.paper_id}
                  isFocused={focusedPaperId === paper.paper_id}
                  isRetrying={retryingPaperId === paper.paper_id}
                  key={paper.paper_id}
                  paperRef={
                    focusedPaperId === paper.paper_id ? focusedPaperRef : undefined
                  }
                  onAssignDomain={handleAssignDomain}
                  onRetryPipeline={(targetPaper) => void handleRetryPipeline(targetPaper)}
                  onReviewConfirm={(targetPaper) => void handleConfirmReview(targetPaper)}
                  paper={paper}
                />
              ))}
              <PaginationBar
                page={page}
                pageSize={PAPER_PAGE_SIZE}
                total={total}
                totalPages={totalPages}
                onNext={() => setPage((current) => Math.min(totalPages, current + 1))}
                onPrevious={() => setPage((current) => Math.max(1, current - 1))}
              />
            </div>
          ) : (
            <EmptyState hasQuery={query.length > 0} />
          )}
        </section>
      </main>

      <ImportPaperDialog
        categories={categories}
        categoryId={importCategoryId}
        error={importError}
        isOpen={isImportOpen}
        isSubmitting={isCreating}
        mode={importMode}
        onCategoryChange={setImportCategoryId}
        onClose={() => {
          if (!isCreating) {
            setIsImportOpen(false);
          }
        }}
        onModeChange={(nextMode) => {
          setImportMode(nextMode);
          setImportValue("");
          setImportError(null);
        }}
        onSubmit={handleCreatePaper}
        onValueChange={setImportValue}
        value={importValue}
      />

      <DomainDialog
        categories={categories}
        error={domainError}
        isOpen={isDomainOpen}
        isSubmitting={isCreatingDomain}
        name={domainName}
        onClose={() => {
          if (!isCreatingDomain) {
            setIsDomainOpen(false);
          }
        }}
        onNameChange={setDomainName}
        onParentChange={setDomainParentId}
        onSubmit={handleCreateDomain}
        parentId={domainParentId}
      />
    </div>
  );
};

function mergePaper(papers: PaperRecord[], nextPaper: PaperRecord): PaperRecord[] {
  const existingIndex = papers.findIndex(
    (paper) => paper.paper_id === nextPaper.paper_id,
  );
  if (existingIndex === -1) {
    return [nextPaper, ...papers].slice(0, PAPER_PAGE_SIZE);
  }
  return papers.map((paper, index) =>
    index === existingIndex ? nextPaper : paper,
  );
}

function flattenCategories(
  categories: CategoryRecord[],
  depth = 0,
): Array<CategoryRecord & { depth: number; label: string }> {
  return categories.flatMap((category) => [
    {
      ...category,
      depth,
      label: `${"  ".repeat(depth)}${depth > 0 ? "- " : ""}${category.name}`,
    },
    ...flattenCategories(category.children ?? [], depth + 1),
  ]);
}

function StatusFilter({
  active = false,
  count,
  icon,
  label,
  onClick,
}: {
  active?: boolean;
  count: number;
  icon: string;
  label: string;
  onClick?: () => void;
}) {
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

function DomainFilter({
  active = false,
  count,
  disabled = false,
  icon,
  label,
  onClick,
  onDelete,
}: {
  active?: boolean;
  count: number;
  disabled?: boolean;
  icon: string;
  label: string;
  onClick: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      className={`group flex w-full items-center rounded-lg transition-colors ${
        active
          ? "bg-surface-container-highest text-primary"
          : "text-on-surface-variant hover:bg-surface-container"
      }`}
    >
      <button
        className="flex min-w-0 flex-1 items-center justify-between rounded-lg px-3 py-2 text-left"
        disabled={disabled}
        onClick={onClick}
        type="button"
      >
        <span className="flex min-w-0 items-center gap-2">
          <span className="material-symbols-outlined text-lg">{icon}</span>
          <span className="truncate text-sm font-semibold">{label}</span>
        </span>
        <span className="ml-2 shrink-0 text-xs font-bold">{count}</span>
      </button>
      <button
        aria-label={`Delete domain ${label.trim()}`}
        className="mr-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-on-surface-variant/60 opacity-70 transition-all hover:bg-error/10 hover:text-error group-hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-40"
        disabled={disabled}
        onClick={(event) => {
          event.stopPropagation();
          onDelete();
        }}
        title="Delete domain"
        type="button"
      >
        <span className="material-symbols-outlined text-base">
          {disabled ? "progress_activity" : "delete"}
        </span>
      </button>
    </div>
  );
}

function DomainDialog({
  categories,
  error,
  isOpen,
  isSubmitting,
  name,
  parentId,
  onClose,
  onNameChange,
  onParentChange,
  onSubmit,
}: {
  categories: CategoryRecord[];
  error: string | null;
  isOpen: boolean;
  isSubmitting: boolean;
  name: string;
  parentId: number | null;
  onClose: () => void;
  onNameChange: (value: string) => void;
  onParentChange: (categoryId: number | null) => void;
  onSubmit: () => void;
}) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-on-background/35 px-4 py-8 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-lg bg-surface-container-lowest p-6 shadow-[0_24px_80px_rgba(22,32,34,0.24)]">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-extrabold text-on-surface">
              Create Domain
            </h2>
            <p className="mt-1 text-sm text-on-surface-variant">
              Use domains to group papers before import and review.
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

        <label
          className="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-on-surface-variant"
          htmlFor="domain-name"
        >
          Domain Name
        </label>
        <input
          autoFocus
          className="w-full rounded-lg border border-outline-variant/40 bg-surface-container-lowest px-3 py-3 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
          id="domain-name"
          name="domain-name"
          onChange={(event) => onNameChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && name.trim() && !isSubmitting) {
              onSubmit();
            }
          }}
          placeholder="e.g. LLM Agents"
          type="text"
          value={name}
        />

        <label
          className="mb-2 mt-4 block text-xs font-bold uppercase tracking-[0.18em] text-on-surface-variant"
          htmlFor="domain-parent"
        >
          Parent Domain
        </label>
        <select
          className="w-full rounded-lg border border-outline-variant/40 bg-surface-container-lowest px-3 py-3 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
          id="domain-parent"
          name="domain-parent"
          onChange={(event) => {
            const nextValue = event.target.value;
            onParentChange(nextValue ? Number(nextValue) : null);
          }}
          value={parentId ?? ""}
        >
          <option value="">Top-level domain</option>
          {flattenCategories(categories).map((category) => (
            <option key={category.category_id} value={category.category_id}>
              {category.label}
            </option>
          ))}
        </select>

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
            disabled={!name.trim() || isSubmitting}
            onClick={onSubmit}
            type="button"
          >
            <span className="material-symbols-outlined text-lg">
              {isSubmitting ? "progress_activity" : "create_new_folder"}
            </span>
            <span>{isSubmitting ? "Creating..." : "Create Domain"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

function PaperCard({
  categories,
  categoryName,
  isAdvancing,
  isAssigningDomain,
  isFocused,
  isRetrying,
  paperRef,
  onAssignDomain,
  onRetryPipeline,
  onReviewConfirm,
  paper,
}: PaperCardProps) {
  const displayStatus = getDisplayStatus(paper);
  const statusColorClass = getStatusColorClass(displayStatus.status);
  const hasPdf = paper.source_pdf_is_real || Boolean(paper.pdf_url);
  const hasNote = Boolean(paper.assets.note) || paper.note_status !== "empty";
  const needsReview = paper.review_status === "waiting_review";
  const isLiveJob =
    paper.latest_job_status === "queued" || paper.latest_job_status === "running";
  const canRetry =
    !isLiveJob &&
    (paper.paper_stage === "error" || paper.latest_job_status === "failed");
  const categoryOptions = flattenCategories(categories);

  return (
    <article
      className={`rounded-lg border bg-surface-container-lowest p-5 shadow-[0_2px_12px_rgba(45,52,53,0.04)] transition-all hover:border-primary/10 hover:shadow-[0_8px_32px_rgba(45,52,53,0.06)] ${
        isFocused ? "border-primary/30 ring-2 ring-primary/15" : "border-transparent"
      }`}
      ref={paperRef}
    >
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <h4
            className="min-w-0 flex-1 overflow-hidden text-ellipsis text-lg font-bold leading-tight text-on-surface transition-colors line-clamp-2 hover:text-primary"
            title={paper.title}
          >
            {paper.title}
          </h4>
          <span
            className={`w-fit shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold ${statusColorClass}`}
          >
            {displayStatus.label}
          </span>
        </div>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 flex-wrap items-center gap-3 text-xs font-medium text-on-surface-variant">
            {paper.year ? <span>{paper.year}</span> : null}
            {paper.venue_short || paper.venue ? (
              <span className="rounded bg-secondary-container px-2 py-0.5 font-bold text-on-secondary-container">
                {paper.venue_short || paper.venue}
              </span>
            ) : null}
            {paper.ccf_rank ? (
              <span className="rounded bg-primary/10 px-2 py-0.5 font-bold text-primary">
                {paper.ccf_rank}
              </span>
            ) : null}
            {paper.sci_quartile ? (
              <span className="rounded bg-secondary/10 px-2 py-0.5 font-bold text-secondary">
                {paper.sci_quartile}
              </span>
            ) : null}
            {paper.doi ? <span className="max-w-[220px] truncate">{paper.doi}</span> : null}
            <span className="rounded bg-surface-container px-2 py-0.5 font-bold text-on-surface-variant">
              {categoryName}
            </span>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3">
            <label className="sr-only" htmlFor={`paper-domain-${paper.paper_id}`}>
              Domain
            </label>
            <select
              className="h-8 max-w-[180px] rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-2 text-xs font-bold text-on-surface-variant outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:opacity-60"
              disabled={isAssigningDomain}
              id={`paper-domain-${paper.paper_id}`}
              onChange={(event) => {
                const nextValue = event.target.value;
                onAssignDomain(
                  paper,
                  nextValue ? Number(nextValue) : null,
                );
              }}
              title="Assign domain"
              value={paper.category_id ?? ""}
            >
              <option value="">No domain</option>
              {categoryOptions.map((category) => (
                <option key={category.category_id} value={category.category_id}>
                  {category.label}
                </option>
              ))}
            </select>
            {needsReview ? (
              <button
                className="flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-bold text-on-primary shadow-sm transition-all disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isAdvancing}
                onClick={() => onReviewConfirm(paper)}
                type="button"
              >
                <span className="material-symbols-outlined text-base">
                  {isAdvancing ? "progress_activity" : "fact_check"}
                </span>
                <span>{isAdvancing ? "Advancing" : "Review Confirm"}</span>
              </button>
            ) : null}
            {canRetry ? (
              <button
                className="flex h-8 items-center gap-1.5 rounded-lg bg-surface-container-high px-3 text-xs font-bold text-on-surface shadow-sm transition-all hover:bg-surface-container-highest disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isRetrying}
                onClick={() => onRetryPipeline(paper)}
                type="button"
              >
                <span className="material-symbols-outlined text-base">
                  {isRetrying ? "progress_activity" : "restart_alt"}
                </span>
                <span>{isRetrying ? "Retrying" : "Retry"}</span>
              </button>
            ) : null}
            <ResourceIcon
              active={hasPdf}
              href={hasPdf ? paperPdfUrl(paper) : undefined}
              icon="picture_as_pdf"
              title="Open PDF"
            />
            <ResourceIcon
              active={hasNote}
              href={hasNote ? paperNoteUrl(paper) : undefined}
              icon="description"
              title="Open Markdown"
            />
          </div>
        </div>
      </div>
    </article>
  );
}

function ResourceIcon({
  active,
  href,
  icon,
  title,
}: {
  active: boolean;
  href?: string;
  icon: string;
  title: string;
}) {
  return (
    <a
      aria-disabled={!active}
      aria-label={title}
      className={`material-symbols-outlined rounded-md text-xl transition-colors ${
        active ? "text-primary" : "text-on-surface-variant/30"
      }`}
      href={active ? href : undefined}
      rel="noreferrer"
      style={{ fontVariationSettings: active ? "'FILL' 1" : "" }}
      target="_blank"
      title={title}
    >
      {icon}
    </a>
  );
}

function FilterChip({
  label,
  onClear,
}: {
  label: string;
  onClear: () => void;
}) {
  return (
    <button
      className="inline-flex items-center gap-1 rounded-full bg-surface-container px-2 py-0.5 text-[10px] font-bold text-on-surface-variant transition-colors hover:bg-surface-container-high"
      onClick={onClear}
      type="button"
    >
      <span>{label}</span>
      <span className="material-symbols-outlined text-sm">close</span>
    </button>
  );
}

function PaginationBar({
  page,
  pageSize,
  total,
  totalPages,
  onNext,
  onPrevious,
}: {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onNext: () => void;
  onPrevious: () => void;
}) {
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(total, page * pageSize);

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-outline-variant/15 bg-surface-container-lowest px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="text-xs font-bold text-on-surface-variant">
        Showing {start}-{end} of {total}
      </div>
      <div className="flex items-center gap-2 self-end sm:self-auto">
        <button
          className="h-9 rounded-lg px-3 text-xs font-bold text-on-surface-variant transition-colors hover:bg-surface-container disabled:cursor-not-allowed disabled:opacity-40"
          disabled={page <= 1}
          onClick={onPrevious}
          type="button"
        >
          Previous
        </button>
        <span className="min-w-20 text-center text-xs font-bold text-on-surface">
          Page {page}/{totalPages}
        </span>
        <button
          className="h-9 rounded-lg px-3 text-xs font-bold text-on-surface-variant transition-colors hover:bg-surface-container disabled:cursor-not-allowed disabled:opacity-40"
          disabled={page >= totalPages}
          onClick={onNext}
          type="button"
        >
          Next
        </button>
      </div>
    </div>
  );
}

function PaperListSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, index) => (
        <div
          className="h-[104px] animate-pulse rounded-lg bg-surface-container-lowest"
          key={index}
        />
      ))}
    </div>
  );
}

function parseOptionalYear(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed)) {
    return null;
  }
  return parsed;
}

function EmptyState({ hasQuery }: { hasQuery: boolean }) {
  return (
    <div className="flex min-h-[280px] flex-col items-center justify-center rounded-lg border border-dashed border-outline-variant/50 bg-surface-container-lowest p-8 text-center">
      <span className="material-symbols-outlined mb-3 text-3xl text-on-surface-variant">
        library_books
      </span>
      <h3 className="text-sm font-bold text-on-surface">
        {hasQuery ? "No matching papers" : "No papers yet"}
      </h3>
      <p className="mt-2 max-w-sm text-sm text-on-surface-variant">
        {hasQuery
          ? "Try another search term."
          : "Use Add Paper to create the first backend-backed library record."}
      </p>
    </div>
  );
}

function getDisplayStatus(paper: PaperRecord): { label: string; status: string } {
  if (paper.review_status === "waiting_review") {
    return { label: "Review Waiting", status: "waiting_review" };
  }
  if (paper.latest_job_type === "paper_resolve_metadata" && paper.latest_job_status === "succeeded") {
    return { label: "Metadata Ready", status: "completed" };
  }
  if (paper.latest_job_status) {
    const jobType = jobTypeLabels[paper.latest_job_type] ?? paper.latest_job_type;
    const jobStatus =
      jobStatusLabels[paper.latest_job_status] ?? paper.latest_job_status;
    return { label: `${jobType} ${jobStatus}`.trim(), status: paper.latest_job_status };
  }
  return {
    label: statusLabels[paper.paper_stage] ?? paper.paper_stage,
    status: paper.paper_stage,
  };
}

function getStatusColorClass(status: string): string {
  switch (status) {
    case "succeeded":
    case "completed":
      return "bg-green-100 text-green-800";
    case "failed":
    case "error":
      return "bg-red-100 text-red-800";
    case "running":
    case "queued":
      return "bg-purple-100 text-purple-800";
    case "waiting_review":
    case "waiting_confirm":
      return "bg-orange-100 text-orange-800";
    case "parsed":
    case "refined":
    case "sectioned":
    case "noted":
      return "bg-blue-100 text-blue-800";
    case "downloaded":
      return "bg-yellow-100 text-yellow-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

function formatError(err: unknown): string {
  if (err instanceof APIError) {
    if (err.code === "PAPER_DUPLICATE") {
      const paperId = err.details.paper_id;
      return paperId
        ? `This paper already exists in Library as paper #${paperId}.`
        : "This paper already exists in Library.";
    }
    return `${err.code}: ${err.message}`;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Unexpected API error.";
}
