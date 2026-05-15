import { AppIcon } from "@/components/ui/AppIcon";
import { type BatchRecord, type CandidateRecord, type PaperRecord } from "@/lib/api";
import { paperSummary } from "@/lib/format";
import { getAcquireActionState, isGate2ReviewPaper } from "@/lib/paperWorkflow";
import { showPlaceholderAction } from "@/lib/placeholder";

type SearchWorkflowViewProps = {
  loading: boolean;
  batches: BatchRecord[];
  candidates: CandidateRecord[];
  candidateBusyId: string;
  candidateQuery: string;
  selectedBatchId: string;
  candidateSourceFilter: string;
  candidateYearSort: CandidateYearSort;
  candidateScoreSort: CandidateScoreSort;
  sourceOptions: string[];
  onCandidateQueryChange: (value: string) => void;
  onSelectedBatchChange: (value: string) => void;
  onCandidateSourceFilterChange: (value: string) => void;
  onCandidateYearSortChange: (value: CandidateYearSort) => void;
  onCandidateScoreSortChange: (value: CandidateScoreSort) => void;
  onCandidateDecision: (candidate: CandidateRecord, decision: "keep" | "reject") => void;
};

type AcquireWorkflowViewProps = {
  loading: boolean;
  queue: PaperRecord[];
  acquireQuery: string;
  currentStageView: AcquireStageView;
  paperActionMap: PaperActionMap;
  onAcquireQueryChange: (value: string) => void;
  onAcquireStageChange: (value: AcquireStageView) => void;
  onSwitchToSearch: () => void;
  onPaperAction: (paper: PaperRecord, action: PaperAction) => void;
};

export type CandidateYearSort = "none" | "desc" | "asc";
export type CandidateScoreSort = "none" | "desc" | "asc";
export type AcquireStageView = "acquire" | "gate2-review";
export type PaperAction = "parse" | "accept" | "reject" | "note";
export type PaperActionMap = Record<string, PaperAction | undefined>;

export function SearchWorkflowView(props: SearchWorkflowViewProps) {
  const filteredCandidates = props.candidates.filter((candidate) => {
    const needle = props.candidateQuery.trim().toLowerCase();
    const batchMatch = props.selectedBatchId === "all" || candidate.batch_id === props.selectedBatchId;
    const sourceMatch = props.candidateSourceFilter === "all" || normalizeSource(candidate.source_type) === props.candidateSourceFilter;
    const haystack = [
      candidate.title,
      candidate.batch_id,
      candidate.venue,
      candidate.authors.join(" "),
      candidate.recommendation_reason,
    ]
      .join(" ")
      .toLowerCase();

    return candidate.decision === "pending" && batchMatch && sourceMatch && (!needle || haystack.includes(needle));
  });

  const sortedCandidates = [...filteredCandidates].sort((left, right) => compareCandidates(left, right, props.candidateYearSort, props.candidateScoreSort));

  return (
    <>
      <section className="panel-card table-panel workflow-panel">
        <div className="panel-head workflow-head">
          <div>
            <h2>Search Batches</h2>
            <span className="panel-subtitle">Review batch coverage first, then move into candidate screening.</span>
          </div>
          <button className="ghost-small" type="button" onClick={() => showPlaceholderAction("Create search batch")}>
            New Search Batch
          </button>
        </div>
        <div className="data-table batch-table">
          <div className="data-row data-head">
            <span>Batch</span>
            <span>Source</span>
            <span>Status</span>
            <span>Pending</span>
            <span>Actions</span>
          </div>
          {props.batches.map((batch) => {
            const pendingTotal = props.candidates.filter((candidate) => candidate.batch_id === batch.batch_id && candidate.decision === "pending").length;
            const isActive = props.selectedBatchId === batch.batch_id;

            return (
              <div className="data-row" key={batch.batch_id}>
                <span className="data-cell-stack">
                  <strong>{prettyBatchTitle(batch)}</strong>
                  <small>{batch.batch_id}</small>
                </span>
                <span className="badge badge-light">{batchSourceSummary(props.candidates, batch.batch_id)}</span>
                <span className={`badge badge-${statusTone(batch.review_status)}`}>{humanizeBatchStatus(batch.review_status)}</span>
                <span>{pendingTotal}</span>
                <span className="row-actions">
                  <button type="button" onClick={() => props.onSelectedBatchChange(isActive ? "all" : batch.batch_id)}>
                    {isActive ? "Clear Focus" : "Focus Batch"}
                  </button>
                </span>
              </div>
            );
          })}
          {!props.loading && props.batches.length === 0 ? <div className="queue-empty">No search batches available.</div> : null}
        </div>
      </section>

      <section className="panel-card table-panel workflow-panel">
        <div className="panel-head workflow-head">
          <div>
            <h2>Candidate Screening</h2>
            <span className="panel-subtitle">
              {props.selectedBatchId === "all" ? "Only pending candidates are shown here." : `Focused batch: ${props.selectedBatchId}`}
            </span>
          </div>
        </div>
        <div className="workflow-filters workflow-filter-grid">
          <input
            aria-label="Search candidates"
            data-primary-search="true"
            onChange={(event) => props.onCandidateQueryChange(event.target.value)}
            placeholder="Search title, author, venue, or recommendation"
            value={props.candidateQuery}
          />
          <select aria-label="Filter by batch" onChange={(event) => props.onSelectedBatchChange(event.target.value)} value={props.selectedBatchId}>
            <option value="all">All Batches</option>
            {props.batches.map((batch) => (
              <option key={batch.batch_id} value={batch.batch_id}>
                {prettyBatchTitle(batch)}
              </option>
            ))}
          </select>
          <select aria-label="Filter by source" onChange={(event) => props.onCandidateSourceFilterChange(event.target.value)} value={props.candidateSourceFilter}>
            <option value="all">All Sources</option>
            {props.sourceOptions.map((source) => (
              <option key={source} value={source}>
                {source}
              </option>
            ))}
          </select>
          <select aria-label="Sort by year" onChange={(event) => props.onCandidateYearSortChange(event.target.value as CandidateYearSort)} value={props.candidateYearSort}>
            <option value="none">Year: None</option>
            <option value="desc">Year: New to Old</option>
            <option value="asc">Year: Old to New</option>
          </select>
          <select aria-label="Sort by score" onChange={(event) => props.onCandidateScoreSortChange(event.target.value as CandidateScoreSort)} value={props.candidateScoreSort}>
            <option value="desc">Score: High to Low</option>
            <option value="asc">Score: Low to High</option>
            <option value="none">Score: None</option>
          </select>
        </div>
        <div className="data-table discover-table">
          <div className="data-row data-head">
            <span>Candidate</span>
            <span>Year</span>
            <span>Source</span>
            <span>AI Score</span>
            <span>Recommendation</span>
            <span>Actions</span>
          </div>
          {sortedCandidates.map((candidate) => {
            const score = candidateAiScore(candidate);
            return (
              <div className="data-row" key={`${candidate.batch_id}-${candidate.candidate_id}`}>
                <span className="data-cell-stack">
                  <strong>{candidate.title}</strong>
                  <small>{candidate.authors.slice(0, 3).join(", ") || candidate.batch_id}</small>
                </span>
                <span>{candidate.year ?? "-"}</span>
                <span className="badge badge-light">{normalizeSource(candidate.source_type)}</span>
                <span>
                  <span className={`score-badge score-${scoreTone(score)}`}>{score}</span>
                </span>
                <span className="recommendation-cell" title={candidate.recommendation_reason || "No recommendation"}>
                  {candidate.recommendation_reason || "No recommendation"}
                </span>
                <span className="row-actions">
                  <button disabled={props.candidateBusyId === candidate.candidate_id} type="button" onClick={() => props.onCandidateDecision(candidate, "keep")}>
                    Keep
                  </button>
                  <button
                    className="danger-action"
                    disabled={props.candidateBusyId === candidate.candidate_id}
                    type="button"
                    onClick={() => props.onCandidateDecision(candidate, "reject")}
                  >
                    Reject
                  </button>
                </span>
              </div>
            );
          })}
          {!props.loading && sortedCandidates.length === 0 ? <div className="queue-empty">No candidates match the current filters.</div> : null}
        </div>
      </section>
    </>
  );
}

export function AcquireWorkflowView(props: AcquireWorkflowViewProps) {
  const filteredQueue = props.queue.filter((paper) => {
    const needle = props.acquireQuery.trim().toLowerCase();
    const haystack = `${paper.title} ${paper.domain} ${paper.area} ${paper.topic} ${paper.venue}`.toLowerCase();
    const stageMatch = props.currentStageView === "acquire" ? true : isGate2ReviewPaper(paper);

    return stageMatch && (!needle || haystack.includes(needle));
  });

  return (
    <section className="panel-card table-panel workflow-panel acquire-table-panel">
      <div className="panel-head workflow-head acquire-table-heading">
        <div className="acquire-table-title-group">
          <div>
            <h2>Acquire</h2>
            <span className="panel-subtitle">Manage full-text acquisition, parsing, review, and promotion into the library.</span>
          </div>
          <div className="workflow-filters acquire-search-row">
            <input
              aria-label="Search acquire queue"
              data-primary-search="true"
              onChange={(event) => props.onAcquireQueryChange(event.target.value)}
              placeholder="Search paper title, domain, area, topic, or venue"
              value={props.acquireQuery}
            />
          </div>
        </div>
        <div className="acquire-toolbar">
          <div className="acquire-stage-tabs" role="tablist" aria-label="Acquire stage switcher">
            <button className="acquire-stage-button" type="button" onClick={props.onSwitchToSearch}>
              <AppIcon name="search" size={16} />
              Search
            </button>
            <button
              className={`acquire-stage-button ${props.currentStageView === "acquire" ? "active" : ""}`}
              type="button"
              onClick={() => props.onAcquireStageChange("acquire")}
            >
              <AppIcon name="download" size={16} />
              Acquire
            </button>
            <button
              className={`acquire-stage-button ${props.currentStageView === "gate2-review" ? "active" : ""}`}
              type="button"
              onClick={() => props.onAcquireStageChange("gate2-review")}
            >
              <AppIcon name="check" size={16} />
              Gate 2 Review
            </button>
          </div>
          <button aria-label="Acquire more actions" className="acquire-menu-button" type="button" onClick={() => showPlaceholderAction("Acquire more actions")}>
            <AppIcon name="more-vertical" size={18} />
          </button>
        </div>
      </div>

      <div className="data-table acquire-table">
        <div className="data-row data-head">
          <span>Paper</span>
          <span>Pipeline Status</span>
          <span>Actions</span>
        </div>
        {filteredQueue.map((paper) => {
          const busyAction = props.paperActionMap[paper.paper_id];
          const actionState = getAcquireActionState(paper);

          return (
            <div className="data-row" key={paper.paper_id}>
              <span className="data-cell-stack acquire-paper-cell">
                <strong>{paper.title}</strong>
                <small>{paperSummary(paper)}</small>
              </span>
              <span className="acquire-pipeline-cell">
                <span className="acquire-pipeline-badges">
                  {buildPipelineBadges(paper).map((item) => (
                    <span className={`pipeline-badge pipeline-badge-${item.tone}`} key={item.label}>
                      <AppIcon name={item.icon} size={15} />
                      {item.label}
                    </span>
                  ))}
                </span>
              </span>
              <span className="row-actions acquire-row-actions acquire-actions-cell">
                {actionState.hasNote ? (
                  <a className="table-link-button acquire-action-button" href={toFileHref(paper.note_path)} rel="noreferrer" target="_blank">
                    <AppIcon name="document" size={17} />
                    Note
                  </a>
                ) : (
                  <button
                    className="acquire-action-button"
                    disabled={Boolean(busyAction) || !actionState.canGenerateNote}
                    type="button"
                    onClick={() => props.onPaperAction(paper, "note")}
                  >
                    <AppIcon name="document" size={17} />
                    Note
                  </button>
                )}
                {actionState.hasPdf ? (
                  <a className="table-link-button acquire-action-button" href={toFileHref(paper.paper_path)} rel="noreferrer" target="_blank">
                    <AppIcon name="download" size={17} />
                    PDF
                  </a>
                ) : (
                  <span aria-disabled="true" className="table-link-button acquire-action-button disabled">
                    <AppIcon name="download" size={17} />
                    PDF
                  </span>
                )}
                <button
                  className="acquire-action-button"
                  disabled={Boolean(busyAction) || !actionState.canParse}
                  type="button"
                  onClick={() => props.onPaperAction(paper, "parse")}
                >
                  <AppIcon name={actionState.parseIcon} size={17} />
                  {actionState.parseLabel}
                </button>
                <button
                  className="acquire-action-button acquire-action-primary"
                  disabled={Boolean(busyAction) || !actionState.canAccept}
                  type="button"
                  onClick={() => props.onPaperAction(paper, "accept")}
                >
                  <AppIcon name="check" size={17} />
                  Accept
                </button>
                <button
                  className="acquire-action-button acquire-action-danger"
                  disabled={Boolean(busyAction) || !actionState.canDelete}
                  type="button"
                  onClick={() => props.onPaperAction(paper, "reject")}
                >
                  <AppIcon name="close" size={17} />
                  Delete
                </button>
              </span>
            </div>
          );
        })}
        {!props.loading && filteredQueue.length === 0 ? <div className="queue-empty">No papers match the current filters.</div> : null}
      </div>
    </section>
  );
}

function buildClassificationItems(paper: PaperRecord) {
  return [
    { label: "Domain", value: paper.domain || "Unassigned" },
    { label: "Area", value: paper.area || "Pending" },
    { label: "Topic", value: paper.topic || "Pending" },
  ] as const;
}

function buildPipelineBadges(paper: PaperRecord) {
  return [
    {
      label: "PDF",
      icon: "download",
      tone: paper.asset_status === "pdf_ready" ? "success" : "warning",
    },
    {
      label: "Parse",
      icon: "file-text",
      tone: paper.parser_status === "parsed" ? "success" : "muted",
    },
    {
      label: "Refine",
      icon: "sparkles",
      tone: paper.refined_review_status === "completed" ? "success" : "muted",
    },
    {
      label: "Check",
      icon: "check-circle",
      tone: paper.read_status === "read" ? "success" : "muted",
    },
    {
      label: "Note",
      icon: "document",
      tone: paper.note_status !== "missing" ? "success" : "muted",
    },
  ] as const;
}

function parserStatusIcon(status: string): "check" | "clock" | "alert" | "play" {
  if (status === "parsed") {
    return "check";
  }
  if (status === "failed") {
    return "alert";
  }
  if (status === "running") {
    return "play";
  }
  return "clock";
}

function parserStatusTone(status: string): "success" | "warning" | "danger" {
  if (status === "parsed") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  return "warning";
}

function humanizeParserStatus(status: string): string {
  switch (status) {
    case "parsed":
      return "Parsed";
    case "failed":
      return "Parse Failed";
    case "running":
      return "Parsing";
    default:
      return "Not Parsed";
  }
}

function compareCandidates(
  left: CandidateRecord,
  right: CandidateRecord,
  yearSort: CandidateYearSort,
  scoreSort: CandidateScoreSort,
): number {
  if (yearSort !== "none") {
    const diff = compareNumber(left.year ?? -1, right.year ?? -1, yearSort);
    if (diff !== 0) {
      return diff;
    }
  }

  if (scoreSort !== "none") {
    const diff = compareNumber(candidateAiScore(left), candidateAiScore(right), scoreSort);
    if (diff !== 0) {
      return diff;
    }
  }

  return left.title.localeCompare(right.title);
}

function compareNumber(left: number, right: number, order: "asc" | "desc"): number {
  return order === "asc" ? left - right : right - left;
}

function candidateAiScore(candidate: CandidateRecord): number {
  return Math.round((candidate.quality + candidate.relevance) / 2);
}

function batchSourceSummary(candidates: CandidateRecord[], batchId: string): string {
  const sources = Array.from(
    new Set(
      candidates
        .filter((candidate) => candidate.batch_id === batchId)
        .map((candidate) => normalizeSource(candidate.source_type)),
    ),
  );
  return sources.slice(0, 2).join(" / ") || "Local";
}

function prettyBatchTitle(batch: BatchRecord): string {
  return batch.title || batch.batch_id.replace(/-/g, " ");
}

function normalizeSource(source: string): string {
  return source || "Local";
}

function scoreTone(score: number): "high" | "mid" | "low" {
  if (score >= 85) {
    return "high";
  }
  if (score >= 70) {
    return "mid";
  }
  return "low";
}

function statusTone(status: string): "success" | "warning" | "danger" | "muted" {
  if (status === "reviewed" || status === "completed") {
    return "success";
  }
  if (status === "pending" || status === "active") {
    return "warning";
  }
  if (status === "failed" || status === "reject") {
    return "danger";
  }
  return "muted";
}

function humanizeBatchStatus(status: string): string {
  switch (status) {
    case "reviewed":
      return "Reviewed";
    case "completed":
      return "Completed";
    case "active":
      return "Active";
    default:
      return "Pending";
  }
}

function toFileHref(path: string): string {
  const normalized = path.replace(/\\/g, "/").replace(/^\/+/, "");
  return `file:///${normalized}`;
}
