import React, { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  APIError,
  listAgentProfiles,
  listLLMStatus,
  listSkillBindings,
  listSkillCatalog,
  type AgentProfileRecord,
  type LLMStatusRecord,
  type SkillBindingRecord,
  type SkillCatalogRecord,
} from "@/lib/api";

export const SettingsPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentProfileRecord[]>([]);
  const [llmStatus, setLlmStatus] = useState<LLMStatusRecord[]>([]);
  const [skillCatalog, setSkillCatalog] = useState<SkillCatalogRecord[]>([]);
  const [skillBindings, setSkillBindings] = useState<SkillBindingRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadSettings(): Promise<void> {
    setIsLoading(true);
    try {
      const [nextAgents, nextLlmStatus, nextCatalog, nextBindings] =
        await Promise.all([
          listAgentProfiles(),
          listLLMStatus(),
          listSkillCatalog(),
          listSkillBindings(),
        ]);
      setAgents(nextAgents);
      setLlmStatus(nextLlmStatus);
      setSkillCatalog(nextCatalog);
      setSkillBindings(nextBindings);
      setError("");
    } catch (err) {
      setError(formatError(err));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadSettings();
  }, []);

  const enabledAgentCount = useMemo(
    () => agents.filter((agent) => agent.enabled).length,
    [agents],
  );
  const healthyLlmCount = useMemo(
    () =>
      llmStatus.filter((status) =>
        ["ok", "disabled"].includes(status.connectivity_status),
      ).length,
    [llmStatus],
  );
  const boundSkillCount = useMemo(
    () => skillBindings.filter((binding) => binding.enabled).length,
    [skillBindings],
  );

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        onPrimaryAction={() => void loadSettings()}
        primaryActionIcon="refresh"
        primaryActionLabel={isLoading ? "Refreshing..." : "Refresh"}
        subtitle="Agents, skills, and model status"
        title="Settings"
      />

      <main className="space-y-6 p-6 sm:p-8">
        {error ? (
          <div className="rounded-xl border border-error/20 bg-red-50 px-4 py-3 text-sm font-semibold text-error">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-3">
          <MetricCard label="Enabled Agents" value={enabledAgentCount} />
          <MetricCard label="LLM Profiles" value={healthyLlmCount} />
          <MetricCard label="Enabled Skills" value={boundSkillCount} />
        </div>

        {isLoading ? (
          <SettingsSkeleton />
        ) : (
          <div className="grid gap-6 xl:grid-cols-2">
            <section className="rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm">
              <h2 className="text-sm font-extrabold text-on-surface">
                Agent Profiles
              </h2>
              <div className="mt-4 space-y-3">
                {agents.map((agent) => (
                  <ConfigRow
                    key={agent.profile_key}
                    meta={`${agent.provider} · ${agent.model_name}`}
                    status={agent.enabled ? "enabled" : "disabled"}
                    title={agent.profile_key}
                  />
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm">
              <h2 className="text-sm font-extrabold text-on-surface">
                LLM Connectivity
              </h2>
              <div className="mt-4 space-y-3">
                {llmStatus.map((status) => (
                  <ConfigRow
                    key={status.profile_key}
                    meta={`${status.provider} · ${status.model_name}${
                      status.ttft_ms ? ` · ${status.ttft_ms}ms` : ""
                    }`}
                    status={status.connectivity_status}
                    title={status.profile_key}
                  />
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm xl:col-span-2">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-sm font-extrabold text-on-surface">
                    Skill Bindings
                  </h2>
                  <p className="mt-1 text-xs text-on-surface-variant">
                    {skillCatalog.length} catalog items, {skillBindings.length} active bindings
                  </p>
                </div>
              </div>
              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                {skillBindings.map((binding) => (
                  <article
                    className="rounded-xl bg-surface-container-low p-4"
                    key={binding.skill_key}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-bold text-on-surface">
                          {binding.skill_key}
                        </h3>
                        <p className="mt-1 text-xs text-on-surface-variant">
                          {binding.scene || "No scene"} · {binding.agent_profile_key}
                        </p>
                      </div>
                      <StatusPill status={binding.enabled ? "enabled" : "disabled"} />
                    </div>
                    <p className="mt-3 text-xs text-on-surface-variant">
                      Tools: {binding.toolset.length ? binding.toolset.join(", ") : "-"}
                    </p>
                  </article>
                ))}
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
};

function ConfigRow({
  meta,
  status,
  title,
}: {
  meta: string;
  status: string;
  title: string;
}) {
  return (
    <article className="flex items-start justify-between gap-4 rounded-xl bg-surface-container-low p-4">
      <div className="min-w-0">
        <h3 className="truncate text-sm font-bold text-on-surface">{title}</h3>
        <p className="mt-1 truncate text-xs text-on-surface-variant">{meta}</p>
      </div>
      <StatusPill status={status} />
    </article>
  );
}

function StatusPill({ status }: { status: string }) {
  const className =
    status === "enabled" || status === "ok"
      ? "bg-green-100 text-green-800"
      : status === "disabled"
        ? "bg-gray-100 text-gray-700"
        : "bg-red-100 text-red-800";
  return (
    <span className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${className}`}>
      {status}
    </span>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-outline-variant/10 bg-surface-container-lowest p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-on-surface-variant">
        {label}
      </p>
      <p className="mt-2 text-3xl font-extrabold text-on-surface">{value}</p>
    </div>
  );
}

function SettingsSkeleton() {
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      {Array.from({ length: 4 }).map((_, index) => (
        <div
          className="h-72 animate-pulse rounded-2xl bg-surface-container-lowest"
          key={index}
        />
      ))}
    </div>
  );
}

function formatError(err: unknown): string {
  if (err instanceof APIError) {
    return `${err.code}: ${err.message}`;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Unexpected config API error.";
}
