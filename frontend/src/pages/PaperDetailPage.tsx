import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { TopBar } from "@/components/layout/TopBar";
import { AppIcon } from "@/components/ui/AppIcon";
import { useDialog } from "@/components/ui/DialogProvider";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  acceptPaper,
  fetchPaper,
  fetchParserRuns,
  generatePaperNote,
  parsePaperPdf,
  rejectPaper,
  type PaperRecord,
  type ParserRunRecord,
} from "@/lib/api";
import { formatDate, paperSummary } from "@/lib/format";
import { getAcquireActionState } from "@/lib/paperWorkflow";

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
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load paper detail."));
  };

  useEffect(load, [paperId]);

  const runAction = (name: string, task: () => Promise<void>) => {
    setBusy(name);
    void task()
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to run paper action."))
      .finally(() => setBusy(""));
  };

  const deleteCurrentPaper = async () => {
    if (!paper) {
      return;
    }
    const accepted = await confirm({
      title: "Delete this paper?",
      message: "This removes the paper directory and all files from the current workflow. This action cannot be undone.",
      confirmLabel: "Delete",
      cancelLabel: "Cancel",
      danger: true,
    });
    if (!accepted) {
      return;
    }

    runAction("delete", async () => {
      await rejectPaper(paper.paper_id);
      navigate("/discover?view=acquire", { replace: true });
    });
  };

  if (!paper) {
    return (
      <>
        <TopBar current="Paper Detail" title="Paper Detail" />
        <main className="page">{error ? <div className="error-banner">{error}</div> : <div className="queue-empty">Loading paper detail...</div>}</main>
      </>
    );
  }

  const actionState = getAcquireActionState(paper);

  return (
    <>
      <TopBar current={paper.title} section="Research Workspace > Workflow > Paper Detail" title="Paper Detail" />
      <main className="page detail-page">
        {error ? <div className="error-banner">{error}</div> : null}

        <section className="panel-card detail-hero">
          <div>
            <Link className="panel-footer-link" to={paper.stage === "library" ? "/library" : "/discover?view=acquire"}>
              {paper.stage === "library" ? "Back to Library" : "Back to Acquire"}
            </Link>
            <h1>{paper.title}</h1>
            <p>{paperSummary(paper)}</p>
            <div className="queue-badges">
              <StatusBadge status={paper.status} />
              <span className="badge badge-muted">{paper.parser_status}</span>
              <span className="badge badge-light">{paper.review_status}</span>
            </div>
          </div>

          <div className="detail-actions">
            <button
              disabled={Boolean(busy) || !actionState.canParse}
              type="button"
              onClick={() =>
                runAction("parse", async () => {
                  await parsePaperPdf(paper.paper_id, paper.parser_status === "failed");
                  load();
                })
              }
            >
              <AppIcon name={actionState.parseIcon} size={16} /> {paper.parser_status === "failed" ? "Retry Parse" : "Parse PDF"}
            </button>
            <button
              disabled={Boolean(busy) || !actionState.canGenerateNote}
              type="button"
              onClick={() =>
                runAction("note", async () => {
                  await generatePaperNote(paper.paper_id, false);
                  load();
                })
              }
            >
              Generate Note
            </button>
            <button
              disabled={Boolean(busy) || !actionState.canAccept}
              type="button"
              onClick={() =>
                runAction("accept", async () => {
                  const response = await acceptPaper(paper.paper_id);
                  navigate(`/library/${encodeURIComponent(response.data.paper_id)}`, { replace: true });
                })
              }
            >
              Accept
            </button>
            <button className="danger-action" disabled={Boolean(busy) || !actionState.canDelete} type="button" onClick={deleteCurrentPaper}>
              Delete Paper
            </button>
          </div>
        </section>

        <section className="grid-row detail-grid">
          <InfoPanel
            title="Workflow State"
            rows={[
              ["Stage", paper.stage || "-"],
              ["Asset", paper.asset_status || "-"],
              ["Parser", paper.parser_status || "-"],
              ["Review", paper.review_status || "-"],
              ["Domain", paper.domain || "-"],
              ["Area", paper.area || "-"],
              ["Topic", paper.topic || "-"],
            ]}
          />
          <InfoPanel
            title="Artifacts"
            rows={[
              ["PDF", paper.paper_path || "missing"],
              ["Note", paper.note_path || "missing"],
              ["Refined", paper.parser_artifacts.refined_path || "missing"],
              ["Parsed text", paper.parser_artifacts.text_path || "missing"],
              ["Sections", paper.parser_artifacts.sections_path || "missing"],
              ["State", paper.state_path || "missing"],
            ]}
          />
        </section>

        <section className="panel-card table-panel">
          <div className="panel-head">
            <h2>Parser Runs</h2>
            <span className="panel-subtitle">{runs.length} run(s)</span>
          </div>
          <div className="data-table">
            <div className="data-row data-head">
              <span>Status</span>
              <span>Parser</span>
              <span>Started</span>
              <span>Finished</span>
              <span>Error</span>
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
            {runs.length === 0 ? <div className="queue-empty">No parser runs yet.</div> : null}
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
