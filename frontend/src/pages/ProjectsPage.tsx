import React from "react";
import { PageHeader } from "@/components/layout/PageHeader";

const projectSections = [
  "Overview",
  "Related Work",
  "Method",
  "Experiment",
  "Conclusion",
  "Manuscript",
] as const;

export const ProjectsPage: React.FC = () => {
  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        primaryActionIcon="add_circle"
        primaryActionLabel="New Block"
        searchPlaceholder="Search project memory, tasks, or linked papers..."
        subtitle="Action Prediction • AAAI 2026"
        title="Projects"
      />

      <main className="grid gap-8 p-6 sm:p-8 xl:grid-cols-[12rem_minmax(0,1fr)]">
        <aside className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest py-3 shadow-sm">
          <div className="mb-4 px-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-on-surface-variant">
              Project Map
            </p>
          </div>
          <nav className="space-y-1 px-2">
            {projectSections.map((section, index) => (
              <button
                key={section}
                className={`flex w-full items-center rounded-2xl px-4 py-2 text-left text-sm transition-colors ${
                  index === 0
                    ? "bg-primary/10 font-bold text-primary"
                    : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                }`}
                type="button"
              >
                {section}
              </button>
            ))}
          </nav>
        </aside>

        <div className="space-y-8">
          <div className="grid gap-6 md:grid-cols-2 2xl:grid-cols-4">
            <div className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
              <p className="text-[12px] font-semibold text-on-surface-variant">
                Submission Window
              </p>
              <div className="mt-2 flex items-baseline space-x-1">
                <span className="text-5xl font-bold tracking-tighter text-on-surface">
                  45
                </span>
                <span className="text-sm font-medium text-on-surface-variant">
                  Days Left
                </span>
              </div>
            </div>

            <div className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
              <p className="text-[12px] font-semibold text-on-surface-variant">
                Papers Linked
              </p>
              <div className="mt-2 flex items-baseline space-x-1">
                <span className="text-5xl font-bold tracking-tighter text-on-surface">
                  42
                </span>
                <span className="text-sm font-medium text-on-surface-variant">
                  Sources
                </span>
              </div>
            </div>

            <div className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
              <p className="text-[12px] font-semibold text-on-surface-variant">
                Views Extracted
              </p>
              <div className="mt-2 flex items-baseline space-x-1">
                <span className="text-5xl font-bold tracking-tighter text-on-surface">
                  18
                </span>
                <span className="text-sm font-medium text-on-surface-variant">
                  Data Views
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
              <div>
                <p className="text-[12px] font-semibold text-on-surface-variant">
                  Progress
                </p>
                <span className="mt-2 block text-2xl font-bold tracking-tight text-on-surface">
                  65%
                </span>
              </div>
              <div className="relative h-16 w-16 rounded-full border-4 border-surface-container">
                <svg
                  className="absolute left-[-4px] top-[-4px] h-full w-full -rotate-90"
                  style={{
                    height: "calc(100% + 8px)",
                    width: "calc(100% + 8px)",
                  }}
                >
                  <circle
                    className="text-primary"
                    cx="36"
                    cy="36"
                    fill="transparent"
                    r="30"
                    stroke="currentColor"
                    strokeDasharray="188"
                    strokeDashoffset="65"
                    strokeWidth="4"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-[10px] font-bold tracking-widest text-primary">
                    DONE
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="overflow-hidden rounded-3xl border border-outline-variant/10 bg-surface-container-low p-8">
            <h3 className="mb-12 text-sm font-bold uppercase tracking-[0.22em] text-on-surface-variant">
              Activity Timeline
            </h3>
            <div className="relative h-24">
              <div className="absolute left-0 right-0 top-1/2 h-[2px] -translate-y-1/2 rounded-full bg-outline-variant/30" />

              <div className="absolute left-[15%] top-0 flex -translate-y-1/2 flex-col items-center">
                <div className="mb-2 rounded-lg border border-outline-variant/10 bg-surface-container-lowest p-3 shadow-sm transition-shadow hover:shadow-md">
                  <p className="whitespace-nowrap text-[11px] font-semibold text-on-surface">
                    Added 5 papers to Related Work
                  </p>
                </div>
                <div className="z-10 h-3 w-3 rounded-full bg-primary ring-4 ring-surface-container-low" />
                <p className="mt-2 text-[10px] font-bold text-on-surface-variant">
                  Yesterday
                </p>
              </div>

              <div className="absolute bottom-0 left-[50%] flex translate-y-1/2 flex-col items-center">
                <p className="mb-2 text-[10px] font-bold text-on-surface-variant">
                  Today 10:30 AM
                </p>
                <div className="z-10 h-3 w-3 rounded-full bg-primary ring-4 ring-surface-container-low" />
                <div className="mt-2 rounded-lg border border-outline-variant/10 bg-surface-container-lowest p-3 shadow-sm transition-shadow hover:shadow-md">
                  <p className="whitespace-nowrap text-[11px] font-semibold text-on-surface">
                    Completed YOLO-World calibration test
                  </p>
                </div>
              </div>

              <div className="absolute left-[85%] top-0 flex -translate-y-1/2 flex-col items-center opacity-50">
                <div className="mb-2 rounded-lg border border-outline-variant/10 bg-surface-container-lowest p-3 shadow-sm">
                  <p className="whitespace-nowrap text-[11px] font-semibold text-on-surface">
                    Manuscript draft v1
                  </p>
                </div>
                <div className="z-10 h-3 w-3 rounded-full bg-outline-variant ring-4 ring-surface-container-low" />
                <p className="mt-2 text-[10px] font-bold text-on-surface-variant">
                  Next Week
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            <div className="rounded-3xl border border-outline-variant/10 bg-surface-container-low/50 p-5">
              <h4 className="mb-4 flex items-center justify-between text-sm font-bold text-on-surface-variant">
                <span>Completed</span>
                <span className="rounded-full bg-surface-container px-2 py-0.5 text-xs">
                  2
                </span>
              </h4>
              <div className="space-y-3">
                <div className="flex items-start space-x-3 rounded-2xl border border-outline-variant/5 bg-surface-container-lowest p-4 opacity-60 shadow-sm">
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-[6px] border border-primary bg-primary">
                    <span className="material-symbols-outlined text-[14px] font-bold text-on-primary">
                      check
                    </span>
                  </div>
                  <p className="text-[13px] font-medium text-on-surface-variant line-through">
                    Identify AAAI 2026 track requirements
                  </p>
                </div>
                <div className="flex items-start space-x-3 rounded-2xl border border-outline-variant/5 bg-surface-container-lowest p-4 opacity-60 shadow-sm">
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-[6px] border border-primary bg-primary">
                    <span className="material-symbols-outlined text-[14px] font-bold text-on-primary">
                      check
                    </span>
                  </div>
                  <p className="text-[13px] font-medium text-on-surface-variant line-through">
                    Export baseline datasets from the library
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-outline-variant/10 bg-surface-container-low/50 p-5">
              <h4 className="mb-4 flex items-center justify-between text-sm font-bold text-primary">
                <span>In Progress</span>
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs">
                  2
                </span>
              </h4>
              <div className="space-y-3">
                <div className="space-y-3 rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-4 shadow-sm transition-colors hover:border-primary/30">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-[13px] font-semibold text-on-surface">
                      Annotate related work gaps
                    </p>
                    <span className="rounded bg-blue-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-blue-800">
                      Method
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-container">
                    <div
                      className="h-full bg-primary"
                      style={{ width: "40%" }}
                    />
                  </div>
                </div>
                <div className="space-y-3 rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-4 shadow-sm transition-colors hover:border-primary/30">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-[13px] font-semibold text-on-surface">
                      Experiment calibration logs
                    </p>
                    <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-800">
                      Results
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-container">
                    <div
                      className="h-full bg-primary"
                      style={{ width: "75%" }}
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-outline-variant/10 bg-surface-container-low/50 p-5">
              <h4 className="mb-4 flex items-center justify-between text-sm font-bold text-on-surface-variant">
                <span>Todo List</span>
                <span className="rounded-full bg-surface-container px-2 py-0.5 text-xs">
                  2
                </span>
              </h4>
              <div className="space-y-3">
                <div className="group flex cursor-pointer items-start space-x-3 rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-4 shadow-sm transition-colors hover:border-primary/30">
                  <div className="mt-0.5 h-5 w-5 shrink-0 rounded-[6px] border-2 border-outline-variant/50 transition-colors group-hover:border-primary" />
                  <p className="text-[13px] font-medium text-on-surface">
                    Prepare ablation study visuals
                  </p>
                </div>
                <div className="group flex cursor-pointer items-start space-x-3 rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-4 shadow-sm transition-colors hover:border-primary/30">
                  <div className="mt-0.5 h-5 w-5 shrink-0 rounded-[6px] border-2 border-outline-variant/50 transition-colors group-hover:border-primary" />
                  <p className="text-[13px] font-medium text-on-surface">
                    Draft conclusion summary
                  </p>
                </div>
                <button
                  className="mt-2 flex w-full items-center justify-center rounded-2xl border-2 border-dashed border-outline-variant/20 py-3 text-xs font-medium text-on-surface-variant transition-all hover:border-primary/30 hover:bg-surface-container-low hover:text-primary"
                  type="button"
                >
                  <span className="material-symbols-outlined mr-1 text-sm">
                    add
                  </span>
                  Add Task
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
