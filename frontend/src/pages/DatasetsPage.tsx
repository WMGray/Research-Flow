import React from "react";
import { PageHeader } from "@/components/layout/PageHeader";

const datasetsDateLabel = new Intl.DateTimeFormat("en-US", {
  weekday: "long",
  month: "long",
  day: "2-digit",
  year: "numeric",
}).format(new Date());

export const DatasetsPage: React.FC = () => {
  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        primaryActionIcon="add_circle"
        primaryActionLabel="New Dataset"
        searchPlaceholder="Search papers, views, or datasets..."
        subtitle={datasetsDateLabel}
        title="Datasets"
      />

      <main className="grid gap-8 p-6 sm:p-8 xl:grid-cols-[18rem_minmax(0,1fr)]">
        <section className="rounded-3xl bg-surface-container-low p-4">
          <div className="mb-4 flex items-center justify-between px-2">
            <h3 className="text-xs font-bold uppercase tracking-[0.22em] text-on-surface-variant">
              Navigation
            </h3>
            <span className="material-symbols-outlined cursor-pointer text-sm text-on-surface-variant">
              unfold_less
            </span>
          </div>

          <div className="space-y-1">
            <div className="group flex cursor-pointer items-center rounded-2xl px-2 py-2 transition-colors hover:bg-surface-container">
              <span className="material-symbols-outlined mr-2 text-sm text-on-surface-variant">
                chevron_right
              </span>
              <span
                className="material-symbols-outlined mr-2 text-lg text-primary"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                folder
              </span>
              <span className="text-sm font-medium text-on-surface">
                Ego-centric Vision
              </span>
            </div>

            <div className="space-y-1">
              <div className="group flex cursor-pointer items-center rounded-2xl px-2 py-2 transition-colors hover:bg-surface-container">
                <span className="material-symbols-outlined mr-2 rotate-90 text-sm text-on-surface-variant">
                  chevron_right
                </span>
                <span className="material-symbols-outlined mr-2 text-lg text-primary">
                  folder_open
                </span>
                <span className="text-sm font-medium text-on-surface">
                  Action Segmentation
                </span>
              </div>

              <div className="space-y-1 pl-8">
                <div className="flex cursor-pointer items-center rounded-xl bg-primary/10 px-3 py-2 text-primary">
                  <span className="material-symbols-outlined mr-2 text-[18px]">
                    description
                  </span>
                  <span className="text-xs font-semibold">
                    EPIC-KITCHENS-100
                  </span>
                </div>
                <div className="flex cursor-pointer items-center rounded-xl px-3 py-2 text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface">
                  <span className="material-symbols-outlined mr-2 text-[18px] opacity-60">
                    description
                  </span>
                  <span className="text-xs">Breakfast Dataset</span>
                </div>
                <div className="flex cursor-pointer items-center rounded-xl px-3 py-2 text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface">
                  <span className="material-symbols-outlined mr-2 text-[18px] opacity-60">
                    description
                  </span>
                  <span className="text-xs">50 Salads</span>
                </div>
              </div>
            </div>

            <div className="group flex cursor-pointer items-center rounded-2xl px-2 py-2 transition-colors hover:bg-surface-container">
              <span className="material-symbols-outlined mr-2 text-sm text-on-surface-variant">
                chevron_right
              </span>
              <span
                className="material-symbols-outlined mr-2 text-lg text-primary"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                folder
              </span>
              <span className="text-sm font-medium text-on-surface">
                MLLM Benchmarks
              </span>
            </div>
          </div>
        </section>

        <section className="space-y-8">
          <div className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-8 shadow-sm">
            <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:justify-between">
              <div className="flex-1 space-y-4">
                <h2 className="text-4xl font-extrabold tracking-tight text-on-surface">
                  EPIC-KITCHENS-100
                </h2>
                <div className="flex flex-wrap gap-2">
                  <span className="rounded-full bg-surface-container-high px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-on-surface">
                    Action Recognition
                  </span>
                  <span className="rounded-full bg-surface-container-high px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-on-surface">
                    2020
                  </span>
                  <span className="rounded-full bg-primary/10 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-primary">
                    Video + Text
                  </span>
                </div>
                <p className="max-w-4xl text-base leading-relaxed text-on-surface-variant">
                  The largest benchmark in egocentric vision, featuring 100
                  hours, 20M frames, and 90,000 action segments across 45
                  kitchens. It captures unscripted daily activities with
                  fine-grained verb, noun, and temporal annotations.
                </p>
              </div>

              <div className="w-full max-w-[420px] shrink-0">
                <div className="aspect-video overflow-hidden rounded-2xl bg-surface-container-high shadow-sm">
                  <div className="flex h-full w-full items-center justify-center bg-slate-300 text-slate-500">
                    <span className="material-symbols-outlined text-4xl">
                      image
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-8 xl:grid-cols-2">
            <div className="flex min-h-[400px] flex-col rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
              <div className="mb-8 flex items-center justify-between">
                <h3 className="text-sm font-bold tracking-tight text-on-surface">
                  Knowledge Graph
                </h3>
                <button
                  className="material-symbols-outlined text-on-surface-variant transition-colors hover:text-primary"
                  type="button"
                >
                  fullscreen
                </button>
              </div>
              <div className="relative flex-1 overflow-hidden rounded-2xl border border-outline-variant/10 bg-surface-container-low/50">
                <div className="absolute left-1/2 top-1/2 z-20 -translate-x-1/2 -translate-y-1/2">
                  <div className="rounded-full bg-primary px-4 py-2 text-xs font-bold text-on-primary shadow-lg shadow-primary/20">
                    EPIC-100
                  </div>
                </div>
                <div className="absolute left-1/4 top-1/4 z-10">
                  <div className="rounded-lg border border-outline-variant/20 bg-surface-container-highest px-3 py-1.5 text-[10px] font-semibold text-on-surface-variant">
                    Video Mamba
                  </div>
                </div>
                <div className="absolute right-1/4 top-1/3 z-10">
                  <div className="rounded-lg border border-outline-variant/20 bg-surface-container-highest px-3 py-1.5 text-[10px] font-semibold text-on-surface-variant">
                    TimeSformer
                  </div>
                </div>
                <div className="absolute bottom-1/4 left-1/3 z-10">
                  <div className="rounded-lg border border-outline-variant/20 bg-surface-container-highest px-3 py-1.5 text-[10px] font-semibold text-on-surface-variant">
                    UniFormer
                  </div>
                </div>
                <div className="absolute bottom-1/4 right-1/4 z-10">
                  <div className="rounded-lg border border-outline-variant/20 bg-surface-container-highest px-3 py-1.5 text-[10px] font-semibold text-on-surface-variant">
                    SlowFast
                  </div>
                </div>
                <svg className="pointer-events-none absolute inset-0 h-full w-full opacity-30">
                  <line
                    stroke="#0078D4"
                    strokeWidth="1"
                    x1="25%"
                    x2="50%"
                    y1="25%"
                    y2="50%"
                  />
                  <line
                    stroke="#0078D4"
                    strokeWidth="1"
                    x1="66%"
                    x2="50%"
                    y1="33%"
                    y2="50%"
                  />
                  <line
                    stroke="#0078D4"
                    strokeWidth="1"
                    x1="33%"
                    x2="50%"
                    y1="66%"
                    y2="50%"
                  />
                  <line
                    stroke="#0078D4"
                    strokeWidth="1"
                    x1="75%"
                    x2="50%"
                    y1="75%"
                    y2="50%"
                  />
                </svg>
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-tr from-surface-container-low via-transparent to-transparent opacity-50" />
              </div>
            </div>

            <div className="space-y-8">
              <div className="flex-1 rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
                <h3 className="mb-6 text-sm font-bold tracking-tight text-on-surface">
                  SOTA Analysis
                </h3>
                <div className="space-y-6">
                  <div className="flex items-end justify-between border-b border-outline-variant/10 pb-4">
                    <div>
                      <span className="mb-1 block text-[10px] font-bold uppercase tracking-[0.22em] text-on-surface-variant">
                        Current SOTA Accuracy
                      </span>
                      <div className="text-4xl font-extrabold text-primary">
                        48.2
                        <span className="ml-1 text-lg opacity-60">%</span>
                      </div>
                    </div>
                    <div className="flex items-center rounded bg-red-100 px-2 py-1 text-xs font-bold text-error">
                      <span className="material-symbols-outlined mr-1 text-sm">
                        trending_up
                      </span>
                      +1.4%
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-on-surface-variant">
                        Top-1 Verb Accuracy
                      </span>
                      <span className="font-bold text-on-surface">67.9%</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-container-high">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: "67.9%" }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-on-surface-variant">
                        Top-1 Noun Accuracy
                      </span>
                      <span className="font-bold text-on-surface">53.4%</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-container-high">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: "53.4%" }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="relative overflow-hidden rounded-3xl bg-primary p-6 shadow-lg shadow-primary/10">
                <div className="relative z-10">
                  <div className="mb-3 flex items-center space-x-2">
                    <span
                      className="material-symbols-outlined text-sm text-on-primary"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      auto_awesome
                    </span>
                    <h4 className="text-xs font-bold uppercase tracking-[0.22em] text-on-primary">
                      AI Trend Analysis
                    </h4>
                  </div>
                  <p className="text-xs italic leading-relaxed text-on-primary/90">
                    "Research is moving from short-range recognition toward
                    long-context temporal reasoning. Transformer baselines are
                    stabilizing on EPIC-100, so the next jump will likely come
                    from multimodal state-space or retrieval-augmented video
                    models."
                  </p>
                </div>
                <div className="absolute -bottom-8 -right-8 h-32 w-32 rounded-full bg-primary-dim opacity-50 blur-2xl" />
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};
