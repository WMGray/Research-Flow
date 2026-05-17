import { CheckCircle2, Database, Folder, Save, Settings, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/app/EmptyState";
import { PageShell } from "@/components/app/PageShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { fetchConfigHealth, fetchSearchAgentSettings, updateSearchAgentSettings, type ConfigHealthData, type SearchAgentSettings } from "@/lib/api";

export function ConfigPage() {
  const [data, setData] = useState<ConfigHealthData | null>(null);
  const [searchAgent, setSearchAgent] = useState<SearchAgentSettings | null>(null);
  const [error, setError] = useState("");
  const [settingsError, setSettingsError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void Promise.all([fetchConfigHealth(), fetchSearchAgentSettings()])
      .then(([configPayload, searchAgentPayload]) => {
        setData(configPayload.data);
        setSearchAgent(searchAgentPayload.data);
        setError("");
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "加载设置失败"));
  }, []);

  const saveSearchAgent = async () => {
    if (!searchAgent) return;
    if (!searchAgent.prompt_template.includes("{keywords}")) {
      setSettingsError("Prompt template 必须包含 {keywords}。");
      return;
    }
    setSaving(true);
    try {
      const response = await updateSearchAgentSettings(searchAgent);
      setSearchAgent(response.data);
      setSettingsError("");
    } catch (err: unknown) {
      setSettingsError(err instanceof Error ? err.message : "保存检索设置失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageShell description="管理本地数据根目录、关键路径、parser 状态，以及新建检索使用的 Codex CLI prompt。" title="设置">
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

      {data ? (
        <>
          <section className="grid gap-3 lg:grid-cols-3">
            <Card className="p-4">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Database className="h-4 w-4 text-muted-foreground" />
                Data Root
              </div>
              <code className="mt-3 block break-all rounded-md bg-muted p-2 text-xs text-muted-foreground">{data.data_root}</code>
            </Card>
            <HealthCard label="Layout" ok={Boolean(data.data_layout)} value={data.data_layout} />
            <HealthCard label="Write Policy" ok={data.write_policy.includes("direct")} value={data.write_policy} />
          </section>

          <section className="grid gap-3 xl:grid-cols-2">
            {Object.entries(data.paths).map(([key, value]) => (
              <Card key={key}>
                <CardHeader className="flex-row items-center justify-between gap-3 pb-3">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <Folder className="h-4 w-4 text-muted-foreground" />
                    {key}
                  </CardTitle>
                  <Badge variant={value.exists && value.is_dir ? "success" : "danger"}>
                    {value.exists && value.is_dir ? "可用" : "缺失"}
                  </Badge>
                </CardHeader>
                <CardContent>
                  <code className="block break-all rounded-md bg-muted p-2 text-xs text-muted-foreground">{value.path}</code>
                </CardContent>
              </Card>
            ))}
          </section>

          <section className="grid gap-3 sm:grid-cols-2">
            <HealthCard label="MinerU SDK" ok={data.parser.mineru_sdk_available} value={data.parser.mineru_sdk_available ? "Available" : "Unavailable"} />
            <HealthCard label="MinerU Token" ok={data.parser.mineru_token_configured} value={data.parser.mineru_token_configured ? "Configured" : "Missing"} />
          </section>

          {searchAgent ? (
            <Card>
              <CardHeader className="flex-row items-center justify-between gap-3 pb-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Settings className="h-4 w-4 text-muted-foreground" />
                  Search Agent
                </CardTitle>
                <Button disabled={saving} size="sm" onClick={() => void saveSearchAgent()}>
                  <Save className="h-4 w-4" />
                  {saving ? "保存中" : "保存"}
                </Button>
              </CardHeader>
              <CardContent className="grid gap-3">
                {settingsError ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{settingsError}</div> : null}
                <label className="grid gap-1.5 text-xs text-muted-foreground">
                  Command template
                  <Input
                    value={searchAgent.command_template}
                    placeholder='例如 codex --exec "{keywords}"'
                    onChange={(event) => setSearchAgent((current) => current ? { ...current, command_template: event.target.value } : current)}
                  />
                </label>
                <label className="grid gap-1.5 text-xs text-muted-foreground">
                  Prompt template
                  <textarea
                    className="min-h-44 rounded-md border bg-background px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring"
                    value={searchAgent.prompt_template}
                    onChange={(event) => setSearchAgent((current) => current ? { ...current, prompt_template: event.target.value } : current)}
                  />
                </label>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="grid gap-1.5 text-xs text-muted-foreground">
                    Default source
                    <Input
                      value={searchAgent.default_source}
                      onChange={(event) => setSearchAgent((current) => current ? { ...current, default_source: event.target.value } : current)}
                    />
                  </label>
                  <label className="grid gap-1.5 text-xs text-muted-foreground">
                    Max results
                    <Input
                      min={1}
                      type="number"
                      value={searchAgent.max_results}
                      onChange={(event) => setSearchAgent((current) => current ? { ...current, max_results: Number(event.target.value) } : current)}
                    />
                  </label>
                </div>
              </CardContent>
            </Card>
          ) : null}
        </>
      ) : (
        <EmptyState description="正在读取运行状态。" icon={Settings} title="加载设置" />
      )}
    </PageShell>
  );
}

function HealthCard({ label, ok, value }: { label: string; ok: boolean; value: string }) {
  const Icon = ok ? CheckCircle2 : TriangleAlert;
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-medium">{label}</div>
          <div className="mt-1 text-xs text-muted-foreground">{value}</div>
        </div>
        <Icon className={ok ? "h-5 w-5 text-emerald-600" : "h-5 w-5 text-amber-600"} />
      </div>
    </Card>
  );
}
