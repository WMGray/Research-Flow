import React from "react";
import { PageHeader } from "@/components/layout/PageHeader";

type DailyPaper = {
  title: string;
  score: number;
  description: string;
};

const papers: DailyPaper[] = [
  {
    title: "Scalable Diffusion Models with Transformers",
    score: 98,
    description:
      "DiT replaces the conventional U-Net backbone with a transformer stack, improving scalability and generation quality on large image synthesis workloads.",
  },
  {
    title: "Language Models are Few-Shot Learners",
    score: 95,
    description:
      "GPT-3 demonstrates that sufficiently large language models can solve diverse NLP tasks with in-context examples instead of parameter updates.",
  },
  {
    title: "SAM: Segment Anything Model",
    score: 92,
    description:
      "SAM introduces a promptable segmentation model that generalizes across objects and scenes, pushing zero-shot interactive segmentation into practice.",
  },
  {
    title: "An Image is Worth 16x16 Words",
    score: 91,
    description:
      "Vision Transformer shows that patchified images can be modeled as token sequences and reach strong classification performance after large-scale pretraining.",
  },
  {
    title: "LoRA: Low-Rank Adaptation of LLMs",
    score: 89,
    description:
      "LoRA injects trainable low-rank matrices into frozen model weights, sharply reducing fine-tuning cost while preserving downstream quality.",
  },
  {
    title: "FlashAttention: Fast and Memory-Efficient",
    score: 87,
    description:
      "FlashAttention reorganizes attention computation around IO efficiency, enabling longer contexts with better throughput and much lower memory pressure.",
  },
  {
    title: "DINOv2: Learning Robust Visual Features",
    score: 85,
    description:
      "DINOv2 scales self-supervised training over curated image corpora and produces visual features that transfer strongly across many downstream tasks.",
  },
  {
    title: "ControlNet: Adding Conditional Control",
    score: 82,
    description:
      "ControlNet adds spatial conditioning branches to diffusion models so generation can follow edges, poses, depth maps, and other structured guidance.",
  },
];

const dateLabel = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "2-digit",
  year: "numeric",
}).format(new Date());

export const DailyPage: React.FC = () => {
  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        primaryActionIcon="add"
        primaryActionLabel="Submit"
        searchPlaceholder="Search academic papers, datasets, or topics..."
        subtitle={dateLabel}
        title="Daily"
      />

      <main className="p-6 sm:p-8">
        <div className="mx-auto max-w-7xl">
          <nav className="mb-8 flex flex-wrap items-center gap-2">
            <button
              className="rounded-full bg-primary px-5 py-2 text-xs font-bold text-on-primary transition-all"
              type="button"
            >
              All
            </button>
            <button
              className="rounded-full bg-surface-container px-5 py-2 text-xs font-semibold text-on-surface-variant transition-all hover:bg-surface-container-highest"
              type="button"
            >
              cs.CV
            </button>
            <button
              className="rounded-full bg-surface-container px-5 py-2 text-xs font-semibold text-on-surface-variant transition-all hover:bg-surface-container-highest"
              type="button"
            >
              cs.CL
            </button>
            <button
              className="rounded-full bg-surface-container px-5 py-2 text-xs font-semibold text-on-surface-variant transition-all hover:bg-surface-container-highest"
              type="button"
            >
              cs.AI
            </button>
            <button
              className="rounded-full bg-surface-container px-5 py-2 text-xs font-semibold text-on-surface-variant transition-all hover:bg-surface-container-highest"
              type="button"
            >
              Recommend
            </button>
          </nav>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
            {papers.map((paper) => (
              <article
                key={paper.title}
                className="group flex h-full flex-col rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm transition-all duration-300 hover:border-primary/20 hover:shadow-md"
              >
                <div className="mb-3 flex items-start justify-between gap-3">
                  <h3 className="pr-2 text-sm font-bold leading-tight text-on-surface line-clamp-2">
                    {paper.title}
                  </h3>
                  <span className="whitespace-nowrap rounded-md bg-primary/10 px-2 py-0.5 text-[10px] font-extrabold text-primary">
                    AI Score: {paper.score}
                  </span>
                </div>

                <p className="mb-6 flex-1 text-[13px] italic leading-relaxed text-on-surface-variant">
                  {paper.description}
                </p>

                <div className="flex items-center justify-between border-t border-surface-container/50 pt-4">
                  <button
                    className="text-xs font-bold text-primary transition-all hover:underline"
                    type="button"
                  >
                    Details
                  </button>
                  <div className="flex items-center gap-3">
                    <button
                      className="text-on-surface-variant transition-colors hover:text-error"
                      type="button"
                    >
                      <span className="material-symbols-outlined text-lg">
                        delete
                      </span>
                    </button>
                    <button
                      className="text-on-surface-variant transition-colors hover:text-primary"
                      type="button"
                    >
                      <span className="material-symbols-outlined text-lg">
                        library_add
                      </span>
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>

          <div className="mt-16 flex items-center justify-center gap-1">
            <button
              className="flex h-10 w-10 items-center justify-center rounded-lg text-on-surface-variant transition-all hover:bg-surface-container"
              type="button"
            >
              <span className="material-symbols-outlined">chevron_left</span>
            </button>
            <button
              className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-sm font-bold text-on-primary"
              type="button"
            >
              1
            </button>
            <button
              className="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold text-on-surface-variant transition-all hover:bg-surface-container"
              type="button"
            >
              2
            </button>
            <span className="flex h-10 w-10 items-center justify-center text-on-surface-variant">
              ...
            </span>
            <button
              className="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold text-on-surface-variant transition-all hover:bg-surface-container"
              type="button"
            >
              5
            </button>
            <button
              className="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold text-on-surface-variant transition-all hover:bg-surface-container"
              type="button"
            >
              6
            </button>
            <button
              className="flex h-10 w-10 items-center justify-center rounded-lg text-on-surface-variant transition-all hover:bg-surface-container"
              type="button"
            >
              <span className="material-symbols-outlined">chevron_right</span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};
