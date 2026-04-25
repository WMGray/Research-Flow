import React from "react";
import { PageHeader } from "@/components/layout/PageHeader";

type InsightCard = {
  type: "Background" | "Method" | "Limitation";
  color: string;
  title: string;
  description: string;
  reference: string;
};

const cards: InsightCard[] = [
  {
    type: "Background",
    color: "bg-blue-50 text-blue-700 border-blue-100",
    title:
      "Long-horizon dependencies in video segmentation remain unresolved, especially once clips exceed several minutes and temporal drift starts compounding.",
    description:
      '"Current architectures struggle to maintain temporal consistency across extended video sequences, leading to fragmented segmentation maps in complex surgical procedures [1]."',
    reference: "Video Mamba, 2024",
  },
  {
    type: "Method",
    color: "bg-emerald-50 text-emerald-700 border-emerald-100",
    title:
      "Separating spatial and temporal attention improves boundary sensitivity and makes subtle action transitions easier to isolate.",
    description:
      '"By decoupling spatial and temporal features, the model better isolates the transitional frames between discrete actions [4]."',
    reference: "MS-TCN++ Revisited, 2023",
  },
  {
    type: "Limitation",
    color: "bg-orange-50 text-orange-700 border-orange-100",
    title:
      "Benchmark imbalance still hurts rare-action recall, so tail categories are frequently absorbed into dominant background classes.",
    description:
      "\"Rarely occurring actions are often misclassified as dominant 'background' activities due to the skewed distribution in standard benchmarks [12].\"",
    reference: "ActionSet Analysis, 2024",
  },
  {
    type: "Background",
    color: "bg-blue-50 text-blue-700 border-blue-100",
    title:
      "Diffusion refiners improve sequence smoothness, but the inference budget remains too expensive for practical real-time segmentation.",
    description:
      '"While diffusion-based refiners offer superior boundary smoothing, the multiple denoising steps prohibit real-time deployment [7]."',
    reference: "DiffAction Net, 2024",
  },
  {
    type: "Method",
    color: "bg-emerald-50 text-emerald-700 border-emerald-100",
    title:
      "Masked self-supervised pretraining reduces annotation dependence by forcing the encoder to recover high-level temporal dynamics from incomplete clips.",
    description:
      '"Reconstructing masked temporal segments forces the latent space to encode high-level action dynamics without human labels [2]."',
    reference: "VideoMAE V2, 2023",
  },
  {
    type: "Limitation",
    color: "bg-orange-50 text-orange-700 border-orange-100",
    title:
      "Heavy occlusion still breaks identity continuity, and current temporal convolutions cannot recover tracks once they fragment.",
    description:
      '"Severe occlusions lead to track fragments that current temporal convolution networks cannot bridge effectively [5]."',
    reference: "CrowdSeg Challenges, 2024",
  },
];

const domains = [
  "Action Segmentation",
  "Online Learning",
  "MLLM Deployment",
  "Temporal Grounding",
  "Efficient Transformers",
  "Human-Object Interaction",
] as const;

export const ViewsPage: React.FC = () => {
  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        primaryActionIcon="add"
        primaryActionLabel="New View"
        searchPlaceholder="Search insights, papers, or domains..."
        subtitle="AI-generated synthesis"
        title="Views"
      />

      <main className="grid gap-8 p-6 sm:p-8 xl:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest py-3 shadow-sm">
          <div className="mb-4 px-4">
            <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-on-surface-variant">
              AI Domains
            </span>
          </div>
          <nav className="space-y-1 px-2">
            {domains.map((domain, index) => (
              <button
                key={domain}
                className={`flex w-full items-center rounded-2xl px-4 py-3 text-left text-sm transition-colors ${
                  index === 0
                    ? "bg-primary/5 font-semibold text-primary"
                    : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                }`}
                type="button"
              >
                {domain}
              </button>
            ))}
          </nav>
        </aside>

        <section className="space-y-8">
          <header>
            <h3 className="mb-2 text-2xl font-bold tracking-tight text-on-surface">
              Action Segmentation
            </h3>
            <p className="max-w-2xl text-sm text-on-surface-variant">
              Fine-grained notes extracted from the reading pipeline, focused on
              temporal reasoning, failure modes, and reusable method patterns.
            </p>
          </header>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 2xl:grid-cols-3">
            {cards.map((card) => (
              <article
                key={card.title}
                className="group flex flex-col gap-4 rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm transition-all hover:border-primary/20 hover:shadow-md"
              >
                <div className="flex justify-start">
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold ${card.color}`}
                  >
                    {card.type}
                  </span>
                </div>
                <h4 className="text-lg font-bold leading-snug text-on-surface">
                  {card.title}
                </h4>
                <p className="text-xs italic leading-relaxed text-on-surface-variant line-clamp-4">
                  {card.description}
                </p>
                <footer className="mt-auto border-t border-surface-container pt-4">
                  <span className="text-[10px] font-medium text-on-surface-variant">
                    Reference: {card.reference}
                  </span>
                </footer>
              </article>
            ))}
          </div>

          <div className="flex items-center justify-center gap-1 rounded-full border border-outline-variant/10 bg-surface-container-lowest/90 px-3 py-1.5 shadow-lg backdrop-blur-md">
            <button
              className="rounded-full p-1 text-on-surface-variant hover:bg-surface-container"
              type="button"
            >
              <span className="material-symbols-outlined text-sm">
                chevron_left
              </span>
            </button>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-bold text-on-primary"
              type="button"
            >
              1
            </button>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-full text-xs text-on-surface transition-colors hover:bg-surface-container"
              type="button"
            >
              2
            </button>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-full text-xs text-on-surface transition-colors hover:bg-surface-container"
              type="button"
            >
              3
            </button>
            <button
              className="rounded-full p-1 text-on-surface-variant hover:bg-surface-container"
              type="button"
            >
              <span className="material-symbols-outlined text-sm">
                chevron_right
              </span>
            </button>
          </div>
        </section>
      </main>
    </div>
  );
};
