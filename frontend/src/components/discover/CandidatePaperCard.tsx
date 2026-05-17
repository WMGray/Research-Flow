import { Check, Info, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { CandidateRecord } from "@/lib/api";
import { authorsText, candidateSummary } from "@/lib/format";
import { candidateScore } from "@/lib/libraryView";
import { cn } from "@/lib/utils";

type CandidatePaperCardProps = {
  candidate: CandidateRecord;
  busy: boolean;
  selected: boolean;
  checked: boolean;
  batchMode: boolean;
  onSelect: () => void;
  onToggle: () => void;
  onDecision: (candidate: CandidateRecord, decision: "keep" | "reject") => void;
};

export function CandidatePaperCard({
  batchMode,
  busy,
  candidate,
  checked,
  onDecision,
  onSelect,
  onToggle,
  selected,
}: CandidatePaperCardProps) {
  const score = candidateScore(candidate);

  return (
    <Card className={cn("p-4 transition-colors hover:border-neutral-400", selected && "border-neutral-500 bg-muted/30")} onClick={onSelect}>
      <div className="flex items-start gap-3">
        <input
          aria-label={`选择 ${candidate.title}`}
          checked={checked}
          className="mt-1 h-4 w-4 rounded border-border"
          type="checkbox"
          onClick={(event) => event.stopPropagation()}
          onChange={onToggle}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="line-clamp-2 text-base font-semibold leading-6">{candidate.title}</h2>
              <p className="mt-1 truncate text-sm text-muted-foreground">{authorsText(candidate.authors)}</p>
            </div>
            <ScoreBadge score={score} />
          </div>

          <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted-foreground">
            {candidate.recommendation_reason || candidateSummary(candidate)}
          </p>

          <div className="mt-4 flex items-center justify-between gap-3">
            <Badge variant="outline">{candidate.batch_id}</Badge>
            <div className="flex shrink-0 gap-2">
              <Button
                size="sm"
                disabled={busy || batchMode}
                title={batchMode ? "多选模式下请使用批量操作栏收录。" : "收录后直接进入文库。"}
                onClick={(event) => {
                  event.stopPropagation();
                  onDecision(candidate, "keep");
                }}
              >
                <Check className="h-4 w-4" />
                收录
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={busy || batchMode}
                title={batchMode ? "多选模式下请使用批量操作栏物理删除。" : "物理删除候选记录和候选产物。"}
                onClick={(event) => {
                  event.stopPropagation();
                  onDecision(candidate, "reject");
                }}
              >
                <X className="h-4 w-4" />
                物理删除
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function ScoreBadge({ score }: { score: number }) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge className="gap-1.5" variant={score >= 85 ? "success" : score >= 70 ? "warning" : "muted"}>
            {score}
            <Info className="h-3 w-3" />
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="max-w-72 leading-5">
          根据关键词匹配、venue 权重、领域相似度、最近更新时间综合计算。
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
