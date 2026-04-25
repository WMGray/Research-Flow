import React from "react";
import { PageHeader } from "@/components/layout/PageHeader";

type PaperCardProps = {
  title: string;
  authors: string;
  ccf: string;
  ccfColorClass: string;
  impactFactor: string;
  quartile: string;
  hasPdf: boolean;
  hasAiNote: boolean;
  hasHumanNote: boolean;
};

const featuredPapers: PaperCardProps[] = [
  {
    title:
      "Multi-modal Large Language Models for Long-form Video Understanding: A Temporal-Causal Approach",
    authors: "Zhang, W., Liu, H., Chen, J., et al.",
    ccf: "CCF-A",
    ccfColorClass: "bg-red-100 text-red-800",
    impactFactor: "15.2",
    quartile: "SCI Q1",
    hasPdf: true,
    hasAiNote: true,
    hasHumanNote: false,
  },
  {
    title:
      "Sparse Token Sampling for Efficient Action Segmentation in Untrimmed Instructional Videos",
    authors: "Kim, D., Nguyen, T., Roberts, P.",
    ccf: "CCF-B",
    ccfColorClass: "bg-secondary-container text-on-secondary-container",
    impactFactor: "8.4",
    quartile: "SCI Q1",
    hasPdf: true,
    hasAiNote: false,
    hasHumanNote: true,
  },
  {
    title:
      "Foundations of Continual Learning: A Comprehensive Survey of Recent Architectural Breakthroughs",
    authors: "Smith, A., Jones, B., Williams, K.",
    ccf: "CCF-A",
    ccfColorClass: "bg-red-100 text-red-800",
    impactFactor: "10.5",
    quartile: "SCI Q1",
    hasPdf: true,
    hasAiNote: true,
    hasHumanNote: true,
  },
  {
    title: "Latent Diffusion for Synthetic Action Recognition Data Generation",
    authors: "Garcia, M., Thompson, S., Lee, Y.",
    ccf: "CCF-B",
    ccfColorClass: "bg-secondary-container text-on-secondary-container",
    impactFactor: "6.9",
    quartile: "SCI Q2",
    hasPdf: false,
    hasAiNote: false,
    hasHumanNote: true,
  },
];

export const LibraryPage: React.FC = () => {
  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        primaryActionIcon="add_circle"
        primaryActionLabel="Add Paper"
        searchPlaceholder="Search papers, authors, or venues..."
        subtitle="Archive and note coverage"
        title="Library"
      />

      <main className="grid gap-8 p-6 sm:p-8 xl:grid-cols-[18rem_minmax(0,1fr)]">
        <section className="flex flex-col rounded-3xl bg-surface-container-low p-6">
          <div className="mb-6 flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-[0.22em] text-on-surface-variant">
              Collections
            </h3>
            <span className="material-symbols-outlined text-sm text-on-surface-variant">
              filter_list
            </span>
          </div>

          <div className="space-y-2">
            <div className="space-y-1">
              <div className="flex cursor-pointer items-center rounded-2xl px-2 py-2 transition-colors hover:bg-surface-container">
                <span className="material-symbols-outlined mr-2 text-lg text-on-surface-variant">
                  arrow_drop_down
                </span>
                <span
                  className="material-symbols-outlined mr-2 text-lg text-primary"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  folder
                </span>
                <span className="text-sm font-medium text-on-surface">
                  MLLM
                </span>
              </div>

              <div className="ml-6 space-y-1">
                <div className="flex cursor-pointer items-center rounded-2xl bg-surface-container-highest px-2 py-2 text-primary">
                  <span className="material-symbols-outlined mr-2 text-lg text-on-surface-variant">
                    arrow_drop_down
                  </span>
                  <span className="material-symbols-outlined mr-2 text-lg">
                    folder_open
                  </span>
                  <span className="text-sm font-semibold">
                    Action Segmentation
                  </span>
                </div>

                <div className="ml-6 space-y-1">
                  <div className="flex cursor-pointer items-center rounded-xl px-2 py-1.5 text-xs text-on-surface-variant transition-colors hover:text-primary">
                    <span className="material-symbols-outlined mr-2 text-sm">
                      description
                    </span>
                    Spatial-Temporal
                  </div>
                  <div className="flex cursor-pointer items-center rounded-xl px-2 py-1.5 text-xs text-on-surface-variant transition-colors hover:text-primary">
                    <span className="material-symbols-outlined mr-2 text-sm">
                      description
                    </span>
                    Weak Supervision
                  </div>
                </div>
              </div>
            </div>

            <div className="flex cursor-pointer items-center rounded-2xl px-2 py-2 transition-colors hover:bg-surface-container">
              <span className="material-symbols-outlined mr-2 text-lg text-on-surface-variant">
                arrow_right
              </span>
              <span
                className="material-symbols-outlined mr-2 text-lg text-on-surface-variant"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                folder
              </span>
              <span className="text-sm font-medium text-on-surface">
                Online Learning
              </span>
            </div>
          </div>

          <div className="mt-8 border-t border-outline-variant/10 pt-6">
            <div className="mb-3 flex items-center justify-between px-1 text-[10px] font-bold uppercase tracking-[0.22em] text-on-surface-variant">
              <span>Storage Usage</span>
              <span className="text-primary">64%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-surface-container shadow-inner">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: "64%" }}
              />
            </div>
          </div>
        </section>

        <section className="flex min-w-0 flex-col">
          <div className="mb-4 flex flex-col gap-3 px-2 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm font-bold text-on-surface">
                124 Papers
              </span>
              <div className="flex gap-2">
                <span className="rounded-full bg-secondary-container px-2 py-0.5 text-[10px] font-bold text-on-secondary-container">
                  RECENT
                </span>
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">
                  CVPR 2024
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                className="rounded-md p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container"
                type="button"
              >
                <span className="material-symbols-outlined text-lg">
                  view_stream
                </span>
              </button>
              <button
                className="rounded-md p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container"
                type="button"
              >
                <span className="material-symbols-outlined text-lg">
                  grid_view
                </span>
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {featuredPapers.map((paper) => (
              <PaperCard key={paper.title} {...paper} />
            ))}
          </div>

          <div className="mt-6 flex items-center justify-center">
            <div className="flex items-center rounded-full bg-surface-container-low p-1.5">
              <button
                className="flex h-8 w-8 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container"
                type="button"
              >
                <span className="material-symbols-outlined text-lg">
                  chevron_left
                </span>
              </button>
              <div className="flex items-center gap-1 px-2">
                <button
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-bold text-on-primary"
                  type="button"
                >
                  1
                </button>
                <button
                  className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium text-on-surface-variant transition-colors hover:bg-surface-container"
                  type="button"
                >
                  2
                </button>
                <button
                  className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium text-on-surface-variant transition-colors hover:bg-surface-container"
                  type="button"
                >
                  3
                </button>
                <span className="px-2 text-xs text-on-surface-variant">
                  ...
                </span>
                <button
                  className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium text-on-surface-variant transition-colors hover:bg-surface-container"
                  type="button"
                >
                  10
                </button>
              </div>
              <button
                className="flex h-8 w-8 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container"
                type="button"
              >
                <span className="material-symbols-outlined text-lg">
                  chevron_right
                </span>
              </button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

function PaperCard({
  title,
  authors,
  ccf,
  ccfColorClass,
  impactFactor,
  quartile,
  hasPdf,
  hasAiNote,
  hasHumanNote,
}: PaperCardProps) {
  return (
    <article className="rounded-3xl border border-transparent bg-surface-container-lowest p-5 shadow-[0_2px_12px_rgba(45,52,53,0.04)] transition-all hover:border-primary/5 hover:shadow-[0_8px_32px_rgba(45,52,53,0.06)]">
      <div className="flex flex-col gap-3">
        <h4 className="text-lg font-bold leading-tight tracking-tight text-on-surface transition-colors hover:text-primary">
          {title}
        </h4>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-3 text-xs font-medium text-on-surface-variant">
            <span className="max-w-[240px] truncate">{authors}</span>
            <span className={`${ccfColorClass} rounded px-2 py-0.5 font-bold`}>
              {ccf}
            </span>
            <span className="font-bold text-secondary">IF: {impactFactor}</span>
            <span className="font-bold text-primary">{quartile}</span>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`material-symbols-outlined text-xl ${
                hasPdf
                  ? "cursor-pointer text-primary"
                  : "cursor-not-allowed text-on-surface-variant/50"
              }`}
              style={{ fontVariationSettings: hasPdf ? "'FILL' 1" : "" }}
            >
              picture_as_pdf
            </span>
            <span
              className={`material-symbols-outlined text-xl ${
                hasAiNote
                  ? "cursor-pointer text-primary"
                  : "cursor-not-allowed text-on-surface-variant/50"
              }`}
              style={{ fontVariationSettings: hasAiNote ? "'FILL' 1" : "" }}
            >
              neurology
            </span>
            <span
              className={`material-symbols-outlined text-xl ${
                hasHumanNote
                  ? "cursor-pointer text-primary"
                  : "cursor-not-allowed text-on-surface-variant/50"
              }`}
              style={{ fontVariationSettings: hasHumanNote ? "'FILL' 1" : "" }}
            >
              person
            </span>
          </div>
        </div>
      </div>
    </article>
  );
}
