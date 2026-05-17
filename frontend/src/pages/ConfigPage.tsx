import { CheckCircle2, Database, Folder, Settings, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/app/EmptyState";
import { PageShell } from "@/components/app/PageShell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchConfigHealth, type ConfigHealthData } from "@/lib/api";

export function ConfigPage() {
  const [data, setData] = useState<ConfigHealthData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetchConfigHealth()
      .then((payload) => {
        setData(payload.data);
        setError("");
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "加载设置失败"));
  }, []);

  return (
    <PageShell description="只读展示本地数据根目录、写入策略、关键路径和 parser 可用性。" title="设置">
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
