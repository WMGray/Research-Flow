import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { AppIcon } from "@/components/ui/AppIcon";
import { useDialog } from "@/components/ui/DialogProvider";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  fetchPaper,
  fetchParserRuns,
  generatePaperNote,
  markPaperProcessed,
  markPaperReview,
  parsePaperPdf,
  rejectPaper,
  type PaperRecord,
  type ParserRunRecord,
} from "@/lib/api";
import { formatDate, paperSummary } from "@/lib/format";

export function PaperDetailPage() {
  const { paperId = "" } = useParams();
  const navigate = useNavigate();
  const { confirm } = useDialog();
  const [paper, setPaper] = useState<PaperRecord | null>(null);
  const [runs, setRuns] = useState<ParserRunRecord[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = () => {
    if (!paperId) {
      return;
    }
    void Promise.all([fetchPaper(paperId), fetchParserRuns(paperId)])
      .then(([paperPayload, runsPayload]) => {
        setPaper(paperPayload.data);
        setRuns(runsPayload.data.items);
        setError("");
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "加载论文详情失败"));
  };

  useEffect(load, [paperId]);

  const action = (name: string, request: Promise<unknown>) => {
    setBusy(name);
    void request
      .then(load)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "执行论文操作失败"))
      .finally(() => setBusy(""));
  };

  const rejectCurrentPaper = async () => {
    if (!paper) {
      return;
    }

    const accepted = await confirm({
      title: "确认删除该论文？",
      message: "该操作会删除论文目录及其全部文件，并将该条目从当前队列中移除。此操作不可恢复。",
      confirmLabel: "确认删除",
      cancelLabel: "取消",
      danger: true,
    });

    if (!accepted) {
      return;
    }

    setBusy("reject");
    void rejectPaper(paper.paper_id)
      .then(() => navigate("/discover?view=acquire", { replace: true }))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "删除论文失败"))
      .finally(() => setBusy(""));
  };

  if (!paper) {
    return (
      <>
        <TopBar current="论文详情" title="论文详情" />
        <main className="page">{error ? <div className="error-banner">{error}</div> : <div className="queue-empty">正在加载论文详情...</div>}</main>
      </>
    );
  }

  return (
    <>
      <TopBar current={paper.title} section="研究工作台 > Workflow > 论文详情" title="论文详情" />
      <main className="page detail-page">
        {error ? <div className="error-banner">{error}</div> : null}
        <section className="panel-card detail-hero">
          <div>
            <Link className="panel-footer-link" to="/discover?view=acquire">
              返回获取队列
            </Link>
            <h1>{paper.title}</h1>
            <p>{paperSummary(paper)}</p>
            <div className="queue-badges">
              <StatusBadge status={paper.status} />
              <span className="badge badge-muted">{paper.parser_status}</span>
              <span className="badge badge-light">{paper.note_status}</span>
            </div>
          </div>
          <div className="detail-actions">
            <button disabled={Boolean(busy)} type="button" onClick={() => action("parse", parsePaperPdf(paper.paper_id, false))}>
              <AppIcon name="play" size={16} /> 解析 PDF
            </button>
            <button disabled={Boolean(busy)} type="button" onClick={() => action("note", generatePaperNote(paper.paper_id, false))}>
              生成笔记
            </button>
            <button disabled={Boolean(busy)} type="button" onClick={() => action("review", markPaperReview(paper.paper_id))}>
              标记待审核
            </button>
            <button disabled={Boolean(busy)} type="button" onClick={() => action("processed", markPaperProcessed(paper.paper_id))}>
              标记已处理
            </button>
            <button className="danger-action" disabled={Boolean(busy)} type="button" onClick={rejectCurrentPaper}>
              删除论文
            </button>
          </div>
        </section>
        <section className="grid-row detail-grid">
          <InfoPanel
            title="基础信息"
            rows={[
              ["Domain", paper.domain || "-"],
              ["Area", paper.area || "-"],
              ["Topic", paper.topic || "-"],
              ["Venue", paper.venue || "-"],
              ["Year", String(paper.year ?? "-")],
              ["DOI", paper.doi || "-"],
            ]}
          />
          <InfoPanel
            title="文件路径"
            rows={[
              ["PDF", paper.paper_path || "missing"],
              ["Note", paper.note_path || "missing"],
              ["Refined", paper.refined_path || "missing"],
              ["Parsed text", paper.parsed_text_path || "missing"],
              ["Sections", paper.parsed_sections_path || "missing"],
              ["State", paper.state_path || "missing"],
            ]}
          />
        </section>
        <section className="panel-card table-panel">
          <div className="panel-head">
            <h2>解析记录</h2>
            <span className="panel-subtitle">共 {runs.length} 次运行</span>
          </div>
          <div className="data-table">
            <div className="data-row data-head">
              <span>状态</span>
              <span>解析器</span>
              <span>开始时间</span>
              <span>结束时间</span>
              <span>错误信息</span>
            </div>
            {runs.map((run) => (
              <div className="data-row" key={run.run_id}>
                <span>
                  <StatusBadge status={run.status} />
                </span>
                <span>{run.parser}</span>
                <span>{formatDate(run.started_at)}</span>
                <span>{formatDate(run.finished_at)}</span>
                <span>{run.error || "-"}</span>
              </div>
            ))}
            {runs.length === 0 ? <div className="queue-empty">还没有解析记录。</div> : null}
          </div>
        </section>
      </main>
    </>
  );
}

function InfoPanel(props: { title: string; rows: Array<[string, string]> }) {
  return (
    <div className="panel-card info-panel">
      <h2>{props.title}</h2>
      {props.rows.map(([label, value]) => (
        <div className="info-line" key={label}>
          <span>{label}</span>
          <strong title={value}>{value}</strong>
        </div>
      ))}
    </div>
  );
}
