import React, { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  type GraphResponse,
  type RecommendationRecord,
  getGraph,
  listRecommendations,
} from "@/lib/api";

export const DiscoveryPage: React.FC = () => {
  const [recommendations, setRecommendations] = useState<RecommendationRecord[]>([]);
  const [graph, setGraph] = useState<GraphResponse>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadDiscovery(): Promise<void> {
      setLoading(true);
      setError("");
      try {
        const [nextRecommendations, nextGraph] = await Promise.all([
          listRecommendations({ limit: 12 }),
          getGraph({ limit: 120 }),
        ]);
        if (!controller.signal.aborted) {
          setRecommendations(nextRecommendations);
          setGraph(nextGraph);
        }
      } catch (exc) {
        if (!controller.signal.aborted) {
          setError(exc instanceof Error ? exc.message : "Failed to load discovery data.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadDiscovery();
    return () => controller.abort();
  }, []);

  const nodeTypes = Array.from(new Set(graph.nodes.map((node) => node.type))).sort();

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        primaryActionIcon="hub"
        primaryActionLabel="Refresh"
        searchPlaceholder="Discovery is computed from backend graph data..."
        subtitle={`${graph.nodes.length} nodes / ${graph.edges.length} edges`}
        title="Discovery"
        onPrimaryAction={() => window.location.reload()}
      />
      <main className="grid gap-6 p-6 sm:p-8 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <section className="space-y-6">
          <header className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-primary">
              Recommendations
            </p>
            <h2 className="text-2xl font-black text-on-surface">
              Next best research actions
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-on-surface-variant">
              Recommendations are computed from stored papers and extracted knowledge. They are
              deterministic, explainable, and avoid pretending to be an online recommender.
            </p>
          </header>

          {error ? (
            <div className="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm font-medium text-error">
              {error}
            </div>
          ) : null}

          {loading ? (
            <div className="grid gap-6 md:grid-cols-2">
              {Array.from({ length: 6 }).map((_, index) => (
                <div className="h-44 animate-pulse rounded-3xl bg-surface-container-low" key={index} />
              ))}
            </div>
          ) : null}

          {!loading && recommendations.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-outline-variant/30 bg-surface-container-lowest p-10 text-center shadow-sm">
              <span className="material-symbols-outlined text-5xl text-on-surface-variant/50">
                explore_off
              </span>
              <h3 className="mt-4 text-xl font-black text-on-surface">
                No recommendations yet
              </h3>
              <p className="mx-auto mt-2 max-w-xl text-sm text-on-surface-variant">
                Import papers and run knowledge extraction to populate the discovery layer.
              </p>
            </div>
          ) : null}

          {!loading && recommendations.length > 0 ? (
            <div className="grid gap-6 md:grid-cols-2">
              {recommendations.map((item) => (
                <article
                  className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm"
                  key={item.recommendation_id}
                >
                  <div className="mb-4 flex items-start justify-between gap-4">
                    <h3 className="text-base font-black leading-snug text-on-surface">
                      {item.title}
                    </h3>
                    <span className="rounded-full bg-primary/10 px-3 py-1 text-[11px] font-bold text-primary">
                      {item.score}
                    </span>
                  </div>
                  <p className="text-sm leading-6 text-on-surface-variant">{item.reason}</p>
                  <div className="mt-5 flex flex-wrap gap-2 border-t border-surface-container pt-4">
                    <Pill label={item.target_type} />
                    <Pill label={item.action} />
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </section>

        <aside className="space-y-6">
          <section className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.22em] text-primary">
              Graph summary
            </p>
            <div className="grid grid-cols-2 gap-3">
              <Stat label="Nodes" value={graph.nodes.length} />
              <Stat label="Edges" value={graph.edges.length} />
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {nodeTypes.map((type) => (
                <Pill key={type} label={type} />
              ))}
            </div>
          </section>

          <section className="rounded-3xl border border-outline-variant/10 bg-surface-container-lowest p-6 shadow-sm">
            <p className="mb-4 text-xs font-bold uppercase tracking-[0.22em] text-on-surface-variant">
              Recent graph nodes
            </p>
            <div className="space-y-3">
              {graph.nodes.slice(0, 10).map((node) => (
                <div className="min-w-0" key={node.id}>
                  <p className="truncate text-sm font-bold text-on-surface">{node.label}</p>
                  <p className="text-xs text-on-surface-variant">{node.type}</p>
                </div>
              ))}
              {graph.nodes.length === 0 ? (
                <p className="text-sm text-on-surface-variant">No graph nodes loaded.</p>
              ) : null}
            </div>
          </section>
        </aside>
      </main>
    </div>
  );
};

function Stat({ label, value }: { label: string; value: number }): React.ReactElement {
  return (
    <div className="rounded-2xl bg-surface-container-low p-4">
      <p className="text-2xl font-black text-primary">{value}</p>
      <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
        {label}
      </p>
    </div>
  );
}

function Pill({ label }: { label: string }): React.ReactElement {
  return (
    <span className="rounded-full bg-surface-container-high px-3 py-1 text-[11px] font-bold text-on-surface-variant">
      {label}
    </span>
  );
}
