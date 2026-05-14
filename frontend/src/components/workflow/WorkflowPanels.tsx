import { Link } from "react-router-dom";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { type BatchRecord, type CandidateRecord, type PaperRecord } from "@/lib/api";
import { formatDate, paperSummary } from "@/lib/format";
import { showPlaceholderAction } from "@/lib/placeholder";

type SearchWorkflowViewProps = {
  loading: boolean;
  batches: BatchRecord[];
  candidates: CandidateRecord[];
  candidateBusyId: string;
  candidateQuery: string;
  selectedBatchId: string;
  candidateSourceFilter: string;
  sourceOptions: string[];
  onCandidateQueryChange: (value: string) => void;
  onSelectedBatchChange: (value: string) => void;
  onCandidateSourceFilterChange: (value: string) => void;
  onCandidateDecision: (candidate: CandidateRecord, decision: "keep" | "reject") => void;
};

type AcquireWorkflowViewProps = {
  loading: boolean;
  queue: PaperRecord[];
  paperBusyId: string;
  acquireQuery: string;
  acquireStatus: string;
  form: IngestForm;
  transferBusy: string;
  onAcquireQueryChange: (value: string) => void;
  onAcquireStatusChange: (value: string) => void;
  onFormChange: (field: keyof IngestForm, value: string | boolean) => void;
  onTransfer: (mode: "ingest" | "migrate") => void;
  onPaperAction: (paper: PaperRecord, action: "parse" | "review" | "reject") => void;
  acquireSummary: Record<string, number>;
};

export type IngestForm = {
  source: string;
  domain: string;
  area: string;
  topic: string;
  target_path: string;
  move: boolean;
};

export function SearchWorkflowView(props: SearchWorkflowViewProps) {
  const batchInsights = buildBatchInsights(props.candidates);
  const filteredCandidates = props.candidates.filter((candidate) => {
    const needle = props.candidateQuery.trim().toLowerCase();
    const batchMatch = props.selectedBatchId === "all" || candidate.batch_id === props.selectedBatchId;
    const sourceMatch = props.candidateSourceFilter === "all" || (candidate.source_type || "local") === props.candidateSourceFilter;
    const haystack = `${candidate.title} ${candidate.batch_id} ${candidate.venue} ${candidate.authors.join(" ")} ${candidate.recommendation_reason}`.toLowerCase();
    return candidate.decision === "pending" && batchMatch && sourceMatch && (!needle || haystack.includes(needle));
  });

  return (
    <>
      <section className="panel-card table-panel workflow-panel">
        <div className="panel-head workflow-head">
          <div>
            <h2>检索批次</h2>
            <span className="panel-subtitle">查看批次覆盖范围、来源构成和当前仍待处理的论文数量。</span>
          </div>
          <button className="ghost-small" type="button" onClick={() => showPlaceholderAction("新建检索批次")}>
            新建检索批次
          </button>
        </div>
        <div className="workflow-filters">
          <input
            aria-label="搜索候选论文"
            data-primary-search="true"
            onChange={(event) => props.onCandidateQueryChange(event.target.value)}
            placeholder="搜索标题、作者、Venue 或批次..."
            value={props.candidateQuery}
          />
          <select aria-label="按批次筛选" onChange={(event) => props.onSelectedBatchChange(event.target.value)} value={props.selectedBatchId}>
            <option value="all">全部批次</option>
            {props.batches.map((batch) => (
              <option key={batch.batch_id} value={batch.batch_id}>
                {prettyBatchTitle(batch)}
              </option>
            ))}
          </select>
          <select aria-label="按来源筛选" onChange={(event) => props.onCandidateSourceFilterChange(event.target.value)} value={props.candidateSourceFilter}>
            <option value="all">全部来源</option>
            {props.sourceOptions.map((source) => (
              <option key={source} value={source}>
                {source}
              </option>
            ))}
          </select>
        </div>
        <div className="data-table batch-table">
          <div className="data-row data-head">
            <span>批次</span>
            <span>来源</span>
            <span>状态</span>
            <span>待查看</span>
            <span>更新时间</span>
            <span>操作</span>
          </div>
          {props.batches.map((batch) => {
            const insight = batchInsights.get(batch.batch_id) ?? emptyBatchInsight();

            return (
              <div className="data-row" key={batch.batch_id}>
                <span>
                  <strong>{prettyBatchTitle(batch)}</strong>
                  <small>{batch.batch_id}</small>
                </span>
                <span className="badge badge-light">{insight.sourceSummary}</span>
                <span className={`badge badge-${statusTone(batch.review_status)}`}>{humanizeBatchStatus(batch.review_status)}</span>
                <span>{insight.pendingTotal}</span>
                <span>{formatDate(batch.updated_at)}</span>
                <span className="row-actions">
                  <button type="button" onClick={() => props.onSelectedBatchChange(batch.batch_id)}>
                    查看候选
                  </button>
                </span>
              </div>
            );
          })}
          {!props.loading && props.batches.length === 0 ? <div className="queue-empty">当前没有可用的检索批次。</div> : null}
        </div>
      </section>

      <section className="panel-card table-panel workflow-panel">
        <div className="panel-head workflow-head">
          <div>
            <h2>候选论文筛选</h2>
            <span className="panel-subtitle">
              {props.selectedBatchId === "all" ? "这里只展示仍待处理的候选论文。" : `当前聚焦批次：${props.selectedBatchId}`}
            </span>
          </div>
          {props.selectedBatchId !== "all" ? (
            <button className="ghost-small" type="button" onClick={() => props.onSelectedBatchChange("all")}>
              清除批次过滤
            </button>
          ) : null}
        </div>
        <div className="data-table discover-table">
          <div className="data-row data-head">
            <span>候选论文</span>
            <span>来源</span>
            <span>推荐理由</span>
            <span>更新时间</span>
            <span>操作</span>
          </div>
          {filteredCandidates.map((candidate) => (
            <div className="data-row" key={`${candidate.batch_id}-${candidate.candidate_id}`}>
              <span>
                <strong>{candidate.title}</strong>
                <small>{candidate.authors.slice(0, 3).join(", ") || candidate.batch_id}</small>
              </span>
              <span className="badge badge-light">{candidate.source_type || "local"}</span>
              <span className="recommendation-cell" title={candidate.recommendation_reason || "暂无推荐理由"}>
                {candidate.recommendation_reason || "暂无推荐理由"}
              </span>
              <span>{formatDate(candidate.updated_at)}</span>
              <span className="row-actions">
                <button disabled={props.candidateBusyId === candidate.candidate_id} type="button" onClick={() => props.onCandidateDecision(candidate, "keep")}>
                  保留
                </button>
                <button
                  className="danger-action"
                  disabled={props.candidateBusyId === candidate.candidate_id}
                  type="button"
                  onClick={() => props.onCandidateDecision(candidate, "reject")}
                >
                  拒绝
                </button>
              </span>
            </div>
          ))}
          {!props.loading && filteredCandidates.length === 0 ? <div className="queue-empty">当前过滤条件下没有候选论文。</div> : null}
        </div>
      </section>
    </>
  );
}

export function AcquireWorkflowView(props: AcquireWorkflowViewProps) {
  const filteredQueue = props.queue.filter((paper) => {
    const needle = props.acquireQuery.trim().toLowerCase();
    const statusMatch = props.acquireStatus === "all" || paper.status === props.acquireStatus;
    const haystack = `${paper.title} ${paper.domain} ${paper.area} ${paper.topic} ${paper.venue}`.toLowerCase();
    return statusMatch && (!needle || haystack.includes(needle));
  });

  return (
    <>
      <section className="grid-row workflow-grid-two">
        <section className="panel-card ingest-panel workflow-panel">
          <div className="panel-head">
            <div>
              <h2>手动入库 / 迁移</h2>
              <span className="panel-subtitle">把 PDF 或论文目录导入到受控库结构中，便于后续解析与沉淀。</span>
            </div>
          </div>
          <div className="ingest-form">
            <label>
              <span>源路径</span>
              <input
                onChange={(event) => props.onFormChange("source", event.target.value)}
                placeholder="C:\\path\\to\\paper-folder-or-paper.pdf"
                value={props.form.source}
              />
            </label>
            <label>
              <span>Domain</span>
              <input onChange={(event) => props.onFormChange("domain", event.target.value)} placeholder="Speech" value={props.form.domain} />
            </label>
            <label>
              <span>Area</span>
              <input onChange={(event) => props.onFormChange("area", event.target.value)} placeholder="Voice Synthesis" value={props.form.area} />
            </label>
            <label>
              <span>Topic</span>
              <input onChange={(event) => props.onFormChange("topic", event.target.value)} placeholder="Singing Voice Synthesis" value={props.form.topic} />
            </label>
            <label className="wide-field">
              <span>目标路径</span>
              <input
                onChange={(event) => props.onFormChange("target_path", event.target.value)}
                placeholder="可选：Library 下的相对路径"
                value={props.form.target_path}
              />
            </label>
            <label className="check-field">
              <input checked={props.form.move} onChange={(event) => props.onFormChange("move", event.target.checked)} type="checkbox" />
              <span>入库时移动源文件</span>
            </label>
            <div className="form-actions">
              <button disabled={props.transferBusy !== ""} type="button" onClick={() => props.onTransfer("ingest")}>
                入库
              </button>
              <button disabled={props.transferBusy !== ""} type="button" onClick={() => props.onTransfer("migrate")}>
                迁移
              </button>
            </div>
          </div>
        </section>

        <section className="panel-card workflow-note-card">
          <h2>Acquire 说明</h2>
          <p>这一视图聚焦已从 Search 阶段保留下来的论文，重点处理 PDF、解析和人工审核。</p>
          <div className="workflow-note-list">
            <div>
              <strong>缺少 PDF</strong>
              <span>{props.acquireSummary.needs_pdf_total ?? 0} 篇论文仍需补齐源 PDF。</span>
            </div>
            <div>
              <strong>待人工审核</strong>
              <span>{props.acquireSummary.needs_review_total ?? 0} 篇论文正在等待人工确认。</span>
            </div>
            <div>
              <strong>解析失败</strong>
              <span>{props.acquireSummary.parse_failed_total ?? 0} 篇论文需要手动排查解析问题。</span>
            </div>
          </div>
        </section>
      </section>

      <section className="panel-card table-panel workflow-panel">
        <div className="panel-head workflow-head">
          <div>
            <h2>Acquire 队列</h2>
            <span className="panel-subtitle">查看已保留论文的 PDF 状态、解析进度和人工审核情况。</span>
          </div>
          <div className="workflow-filters workflow-filters-inline">
            <input
              aria-label="搜索 Acquire 队列"
              data-primary-search="true"
              onChange={(event) => props.onAcquireQueryChange(event.target.value)}
              placeholder="搜索论文、领域、主题..."
              value={props.acquireQuery}
            />
            <select aria-label="按状态筛选 Acquire 队列" onChange={(event) => props.onAcquireStatusChange(event.target.value)} value={props.acquireStatus}>
              <option value="all">全部状态</option>
              <option value="needs-pdf">缺少 PDF</option>
              <option value="needs-review">待审核</option>
              <option value="processed">已处理</option>
              <option value="parse-failed">解析失败</option>
              <option value="rejected">已拒绝</option>
            </select>
          </div>
        </div>
        <div className="data-table acquire-table">
          <div className="data-row data-head">
            <span>论文</span>
            <span>Domain</span>
            <span>Area</span>
            <span>Topic</span>
            <span>状态</span>
            <span>操作</span>
          </div>
          {filteredQueue.map((paper) => (
            <div className="data-row" key={paper.paper_id}>
              <span>
                <strong>{paper.title}</strong>
                <small>{paperSummary(paper)}</small>
              </span>
              <span>{paper.domain || "unclassified"}</span>
              <span>{paper.area || "-"}</span>
              <span>{paper.topic || "-"}</span>
              <span>
                <StatusBadge status={paper.status} />
              </span>
              <span className="row-actions">
                <button disabled={props.paperBusyId === paper.paper_id} type="button" onClick={() => props.onPaperAction(paper, "parse")}>
                  解析
                </button>
                <Link to={`/library/${encodeURIComponent(paper.paper_id)}`}>查看</Link>
                <button disabled={props.paperBusyId === paper.paper_id} type="button" onClick={() => props.onPaperAction(paper, "review")}>
                  审核
                </button>
                <button className="danger-action" disabled={props.paperBusyId === paper.paper_id} type="button" onClick={() => props.onPaperAction(paper, "reject")}>
                  删除
                </button>
              </span>
            </div>
          ))}
          {!props.loading && filteredQueue.length === 0 ? <div className="queue-empty">当前过滤条件下没有论文。</div> : null}
        </div>
      </section>
    </>
  );
}

function buildBatchInsights(candidates: CandidateRecord[]): Map<string, BatchInsight> {
  const grouped = new Map<string, CandidateRecord[]>();
  for (const candidate of candidates) {
    const rows = grouped.get(candidate.batch_id) ?? [];
    rows.push(candidate);
    grouped.set(candidate.batch_id, rows);
  }

  return new Map(
    Array.from(grouped.entries()).map(([batchId, rows]) => {
      const sources = Array.from(new Set(rows.map((row) => row.source_type || "local")));
      const pendingTotal = rows.filter((row) => row.decision === "pending").length;
      return [
        batchId,
        {
          sourceSummary: sources.slice(0, 2).join(", "),
          pendingTotal,
        },
      ];
    }),
  );
}

function emptyBatchInsight(): BatchInsight {
  return {
    sourceSummary: "local",
    pendingTotal: 0,
  };
}

function prettyBatchTitle(batch: BatchRecord): string {
  return batch.title || batch.batch_id.replace(/-/g, " ");
}

function statusTone(status: string): "success" | "warning" | "danger" | "muted" {
  if (status === "keep" || status === "active" || status === "processed") {
    return "success";
  }
  if (status === "pending" || status === "draft" || status === "needs-review" || status === "needs-pdf") {
    return "warning";
  }
  if (status === "reject" || status === "rejected" || status === "parse-failed" || status === "failed") {
    return "danger";
  }
  return "muted";
}

function humanizeBatchStatus(status: string): string {
  if (status === "active") {
    return "进行中";
  }
  if (status === "completed") {
    return "已完成";
  }
  if (status === "draft") {
    return "草稿";
  }
  if (status === "reviewed") {
    return "已复核";
  }
  return status;
}

type BatchInsight = {
  sourceSummary: string;
  pendingTotal: number;
};
