import { ArrowRight, Bot, Check, ChevronRight, Layers, ListChecks, SkipForward, Tags } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/app/EmptyState";
import { PageShell } from "@/components/app/PageShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useDialog } from "@/components/ui/DialogProvider";
import { fetchPapersDashboard, updatePaperClassification, type PaperRecord } from "@/lib/api";
import { formatDate } from "@/lib/format";
import {
  DOMAIN_TREE_SEEDS,
  type MissingField,
  localClassifySuggestion,
  missingFieldsForPaper,
} from "@/lib/libraryView";
import { cn } from "@/lib/utils";

type ClassificationDraft = {
  domain: string;
  area: string;
  topic: string;
  tags: string;
  confidence: number;
};

type QueueGroup = {
  id: string;
  label: string;
  items: PaperRecord[];
};

type TriageStats = {
  total: number;
  missingDomain: number;
  missingTopic: number;
  missingPdf: number;
  pendingRefine: number;
};

export function UncategorizedPage() {
  const { notify } = useDialog();
  const [papers, setPapers] = useState<PaperRecord[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState("");
  const [draft, setDraft] = useState<ClassificationDraft>(emptyDraft());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [complete, setComplete] = useState(false);

  const load = async (): Promise<PaperRecord[]> => {
    setLoading(true);
    try {
      const payload = await fetchPapersDashboard();
      const queue = payload.data.papers.filter(isTriagePaper);
      setPapers(queue);
      setError("");
      return queue;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load unclassified papers");
      return [];
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load().then((queue) => {
      const first = queue[0] ?? null;
      setSelectedPaperId(first?.paper_id ?? "");
      setComplete(queue.length === 0);
    });
  }, []);

  const selectedPaper = selectedPaperId ? papers.find((paper) => paper.paper_id === selectedPaperId) ?? null : null;
  const queueGroups = useMemo(() => buildQueueGroups(papers), [papers]);
  const stats = useMemo(() => triageStats(papers), [papers]);
  const domains = useMemo(() => DOMAIN_TREE_SEEDS.filter((node) => node.level === "domain").map((node) => node.label), []);

  useEffect(() => {
    if (!selectedPaper) {
      setDraft(emptyDraft());
      return;
    }
    setSelectedPaperId(selectedPaper.paper_id);
    setComplete(false);
    setDraft({
      domain: selectedPaper.domain,
      area: selectedPaper.area,
      topic: selectedPaper.topic,
      tags: selectedPaper.tags.join(", "),
      confidence: 0,
    });
  }, [selectedPaper?.paper_id]);

  const saveAndNext = async () => {
    if (!selectedPaper) return;
    const nextId = nextPaperId(papers, selectedPaper.paper_id);
    await updatePaperClassification(selectedPaper.paper_id, {
      domain: draft.domain,
      area: draft.area,
      topic: draft.topic,
      tags: splitTags(draft.tags),
    });
    const queue = await load();
    const nextSelection = nextId ? (queue.some((paper) => paper.paper_id === nextId) ? nextId : queue[0]?.paper_id ?? "") : "";
    setSelectedPaperId(nextSelection);
    setComplete(!nextSelection);
    notify({
      title: "Classification saved",
      message: nextSelection ? "Moved to the next paper in the triage queue." : "No remaining papers in this queue.",
    });
  };

  const skip = () => {
    if (!selectedPaper) return;
    const nextId = nextPaperId(papers, selectedPaper.paper_id);
    setSelectedPaperId(nextId ?? "");
    setComplete(!nextId);
  };

  const autoSuggest = () => {
    if (!selectedPaper) return;
    const suggestedClassification = localClassifySuggestion(selectedPaper);
    setDraft({
      domain: suggestedClassification.domain,
      area: suggestedClassification.area,
      topic: suggestedClassification.topic,
      tags: suggestedClassification.tags.join(", "),
      confidence: suggestedClassification.confidence,
    });
  };

  return (
    <PageShell
      actions={
        <Button asChild size="sm" variant="outline">
          <Link to="/papers">
            Back to Library
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      }
      description="Triage papers with missing classification, missing PDFs, or pending refine review."
      title="Unclassified Triage"
    >
      {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

      <StatsGrid stats={stats} />

      {complete && !loading ? (
        <EmptyState description="There are no remaining papers in this triage queue." icon={Check} title="Triage complete" />
      ) : (
        <section className="grid min-h-[640px] gap-4 xl:grid-cols-[320px_minmax(420px,1fr)_360px]">
          <QueuePanel groups={queueGroups} selectedPaperId={selectedPaper?.paper_id ?? ""} onSelect={(paper) => setSelectedPaperId(paper.paper_id)} />
          <EvidencePanel paper={selectedPaper} />
          <EditorPanel
            domains={domains}
            draft={draft}
            paper={selectedPaper}
            onAutoSuggest={autoSuggest}
            onDraftChange={setDraft}
            onSaveAndNext={() => void saveAndNext()}
            onSkip={skip}
          />
        </section>
      )}
    </PageShell>
  );
}

function StatsGrid({ stats }: { stats: TriageStats }) {
  const cards: Array<{ label: string; value: number }> = [
    { label: "Total", value: stats.total },
    { label: "Missing Domain", value: stats.missingDomain },
    { label: "Missing Topic", value: stats.missingTopic },
    { label: "Missing PDF", value: stats.missingPdf },
    { label: "Pending Refine", value: stats.pendingRefine },
  ];

  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      {cards.map((card) => (
        <Card className="p-3" key={card.label}>
          <div className="text-xs font-medium uppercase text-muted-foreground">{card.label}</div>
          <div className="mt-2 text-2xl font-semibold">{card.value}</div>
        </Card>
      ))}
    </section>
  );
}

function QueuePanel({ groups, onSelect, selectedPaperId }: { groups: QueueGroup[]; selectedPaperId: string; onSelect: (paper: PaperRecord) => void }) {
  return (
    <Card className="min-h-0 overflow-hidden">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <ListChecks className="h-4 w-4 text-muted-foreground" />
          Queue
        </CardTitle>
      </CardHeader>
      <CardContent className="min-h-0 overflow-auto">
        <div className="grid gap-4">
          {groups.map((group) => (
            <div className="grid gap-2" key={group.id}>
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-xs font-semibold uppercase text-muted-foreground">{group.label}</h3>
                <Badge variant="outline">{group.items.length}</Badge>
              </div>
              <div className="grid gap-1.5">
                {group.items.map((paper) => (
                  <button
                    className={cn(
                      "grid gap-1 rounded-md border px-3 py-2 text-left transition-colors hover:border-foreground/30 hover:bg-muted/40",
                      selectedPaperId === paper.paper_id && "border-foreground/40 bg-muted/60",
                    )}
                    key={`${group.id}-${paper.paper_id}`}
                    type="button"
                    onClick={() => onSelect(paper)}
                  >
                    <span className="line-clamp-2 text-sm font-medium leading-5">{paper.title}</span>
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      {paper.venue || "No venue"}
                      <ChevronRight className="h-3 w-3" />
                      {paper.year ?? "No year"}
                    </span>
                  </button>
                ))}
                {group.items.length === 0 ? <div className="rounded-md bg-muted/40 px-3 py-2 text-xs text-muted-foreground">No papers in this group.</div> : null}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function EvidencePanel({ paper }: { paper: PaperRecord | null }) {
  if (!paper) {
    return <EmptyState className="min-h-[420px] bg-muted/30" description="Select a queue item to inspect its evidence." icon={Layers} title="No paper selected" />;
  }

  return (
    <Card className="min-h-0 overflow-hidden">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Paper Evidence</CardTitle>
      </CardHeader>
      <CardContent className="min-h-0 overflow-auto">
        <div className="grid gap-4">
          <div>
            <h2 className="text-xl font-semibold leading-7">{paper.title}</h2>
            <div className="mt-3 flex flex-wrap gap-1.5">
              <StatusBadge status={paper.asset_status === "missing_pdf" || !paper.paper_path ? "missing_pdf" : "pdf_ready"} />
              <StatusBadge status={paper.refined_review_status || "missing"} />
              <StatusBadge status={paper.classification_status || "pending"} />
            </div>
          </div>

          <EvidenceBlock title="Abstract">
            <p className="text-sm leading-6 text-muted-foreground">
              {paper.abstract || "暂无真实 abstract。请刷新元数据或手动补充。"}
            </p>
          </EvidenceBlock>

          <EvidenceBlock title="Metadata">
            <div className="grid gap-2 text-sm">
              <MetaRow label="Venue" value={paper.venue || "No venue"} />
              <MetaRow label="Year" value={paper.year ? String(paper.year) : "No year"} />
              <MetaRow label="Updated" value={formatDate(paper.updated_at)} />
            </div>
          </EvidenceBlock>

          <EvidenceBlock title="Tags">
            <TagList tags={paper.tags} />
          </EvidenceBlock>

          <EvidenceBlock title="Existing Classification">
            <div className="grid gap-2 text-sm">
              <MetaRow label="Domain" value={paper.domain || "Missing"} />
              <MetaRow label="Area" value={paper.area || "Missing"} />
              <MetaRow label="Topic" value={paper.topic || "Missing"} />
            </div>
          </EvidenceBlock>
        </div>
      </CardContent>
    </Card>
  );
}

function EditorPanel({
  domains,
  draft,
  onAutoSuggest,
  onDraftChange,
  onSaveAndNext,
  onSkip,
  paper,
}: {
  domains: string[];
  draft: ClassificationDraft;
  paper: PaperRecord | null;
  onAutoSuggest: () => void;
  onDraftChange: (draft: ClassificationDraft) => void;
  onSaveAndNext: () => void;
  onSkip: () => void;
}) {
  return (
    <Card className="min-h-0 overflow-hidden">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Classification</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <label className="grid gap-1">
          <span className="text-xs text-muted-foreground">Domain</span>
          <Select value={draft.domain || "none"} onValueChange={(value) => onDraftChange({ ...draft, domain: value === "none" ? "" : value })}>
            <SelectTrigger>
              <SelectValue placeholder="Select Domain" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Unspecified</SelectItem>
              {domains.map((domain) => (
                <SelectItem key={domain} value={domain}>
                  {domain}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <TextField label="Area" value={draft.area} onChange={(value) => onDraftChange({ ...draft, area: value })} />
        <TextField label="Topic" value={draft.topic} onChange={(value) => onDraftChange({ ...draft, topic: value })} />
        <TextField label="Tags" value={draft.tags} onChange={(value) => onDraftChange({ ...draft, tags: value })} />
        <label className="grid gap-1">
          <span className="text-xs text-muted-foreground">Confidence</span>
          <Input readOnly value={draft.confidence ? `${draft.confidence}%` : "Not calculated"} />
        </label>
        <div className="grid gap-2 pt-1">
          <Button size="sm" variant="outline" disabled={!paper} onClick={onAutoSuggest}>
            <Bot className="h-4 w-4" />
            Auto Suggest
          </Button>
          <Button size="sm" disabled={!paper} onClick={onSaveAndNext}>
            Save and Next
          </Button>
          <Button size="sm" variant="secondary" disabled={!paper} onClick={onSkip}>
            <SkipForward className="h-4 w-4" />
            Skip
          </Button>
        </div>
        <p className="text-xs leading-5 text-muted-foreground">Auto Suggest 仅基于本地标题、标签和分类字段给出建议。</p>
      </CardContent>
    </Card>
  );
}

function EvidenceBlock({ children, title }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-md border bg-background p-3">
      <h3 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">{title}</h3>
      {children}
    </section>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 border-t py-2 first:border-t-0 first:pt-0 last:pb-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="min-w-0 max-w-[70%] truncate text-right font-medium" title={value}>
        {value}
      </span>
    </div>
  );
}

function TagList({ tags }: { tags: string[] }) {
  if (tags.length === 0) {
    return <Badge variant="muted">No tags</Badge>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((tag) => (
        <Badge key={tag} variant="muted">
          {tag}
        </Badge>
      ))}
    </div>
  );
}

function TextField({ label, onChange, value }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function buildQueueGroups(papers: PaperRecord[]): QueueGroup[] {
  const missingFieldGroups: QueueGroup[] = (["Domain", "Area", "Topic", "Tags"] satisfies MissingField[]).map((field) => ({
    id: `missing-${field.toLowerCase()}`,
    label: `Missing ${field}`,
    items: papers.filter((paper) => missingFieldsForPaper(paper).includes(field)),
  }));

  return [
    ...missingFieldGroups,
    {
      id: "missing-pdf",
      label: "Missing PDF",
      items: papers.filter(isMissingPdf),
    },
    {
      id: "pending-refine",
      label: "Pending Refine",
      items: papers.filter(isPendingRefine),
    },
  ];
}

function triageStats(papers: PaperRecord[]): TriageStats {
  return {
    total: papers.length,
    missingDomain: papers.filter((paper) => missingFieldsForPaper(paper).includes("Domain")).length,
    missingTopic: papers.filter((paper) => missingFieldsForPaper(paper).includes("Topic")).length,
    missingPdf: papers.filter(isMissingPdf).length,
    pendingRefine: papers.filter(isPendingRefine).length,
  };
}

function isTriagePaper(paper: PaperRecord): boolean {
  return missingFieldsForPaper(paper).length > 0 || isMissingPdf(paper) || isPendingRefine(paper);
}

function isMissingPdf(paper: PaperRecord): boolean {
  return paper.asset_status === "missing_pdf" || !paper.paper_path;
}

function isPendingRefine(paper: PaperRecord): boolean {
  return paper.refined_review_status === "pending" || paper.workflow_status === "refine_review_pending";
}

function nextPaperId(papers: PaperRecord[], currentPaperId: string): string | null {
  const currentIndex = papers.findIndex((paper) => paper.paper_id === currentPaperId);
  if (currentIndex < 0) return papers[0]?.paper_id ?? null;
  return papers[currentIndex + 1]?.paper_id ?? null;
}

function splitTags(value: string): string[] {
  return value
    .split(/[,\n，]/)
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function emptyDraft(): ClassificationDraft {
  return {
    domain: "",
    area: "",
    topic: "",
    tags: "",
    confidence: 0,
  };
}
