import { useEffect, useState } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { AppIcon } from "@/components/ui/AppIcon";
import { fetchConfigHealth, type ConfigHealthData } from "@/lib/api";

export function ConfigPage() {
  const [data, setData] = useState<ConfigHealthData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetchConfigHealth()
      .then((payload) => setData(payload.data))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "加载配置健康度失败"));
  }, []);

  return (
    <>
      <TopBar current="配置" section="研究工作台 > 配置" title="配置" />
      <main className="page config-page">
        <section className="workflow-hero config-hero">
          <div className="workflow-hero-icon">
            <AppIcon name="settings" size={40} />
          </div>
          <div>
            <h1>运行时配置健康度</h1>
            <p>只读查看本地数据根目录、解析能力和关键目录的可用状态。</p>
          </div>
        </section>
        {error ? <div className="error-banner">{error}</div> : null}
        {data ? (
          <>
            <section className="panel-card">
              <h2>数据根目录</h2>
              <code className="path-code">{data.data_root}</code>
            </section>
            <section className="grid-row config-grid">
              {Object.entries(data.paths).map(([key, value]) => (
                <div className="panel-card config-tile" key={key}>
                  <span className={`badge badge-${value.exists && value.is_dir ? "success" : "danger"}`}>
                    {value.exists && value.is_dir ? "可用" : "缺失"}
                  </span>
                  <h2>{key}</h2>
                  <code>{value.path}</code>
                </div>
              ))}
            </section>
            <section className="panel-card parser-health">
              <h2>解析器健康度</h2>
              <Health label="MinerU SDK" ok={data.parser.mineru_sdk_available} />
              <Health label="MinerU Token" ok={data.parser.mineru_token_configured} />
              <Health label="PyMuPDF Fallback" ok={data.parser.pymupdf_available} />
            </section>
          </>
        ) : null}
      </main>
    </>
  );
}

function Health(props: { label: string; ok: boolean }) {
  return (
    <div className="health-row">
      <span>{props.label}</span>
      <strong className={`badge badge-${props.ok ? "success" : "warning"}`}>{props.ok ? "可用" : "不可用"}</strong>
    </div>
  );
}
