import { SlidersHorizontal, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { BatchRecord } from "@/lib/api";

export type DiscoverFilterState = {
  batchId: string;
  minScore: number;
  maxScore: number;
};

type DiscoverFiltersProps = {
  filters: DiscoverFilterState;
  batches: BatchRecord[];
  onChange: (filters: DiscoverFilterState) => void;
  onClear: () => void;
};

export function DiscoverFilters({ batches, filters, onChange, onClear }: DiscoverFiltersProps) {
  const set = <K extends keyof DiscoverFilterState>(key: K, value: DiscoverFilterState[K]) => {
    onChange({ ...filters, [key]: value });
  };

  return (
    <section className="rounded-lg border bg-card p-3">
      <div className="grid gap-3 lg:grid-cols-[minmax(0,220px)_minmax(0,1fr)_auto] lg:items-center">
        <Select value={filters.batchId} onValueChange={(value) => set("batchId", value)}>
          <SelectTrigger className="h-9">
            <SelectValue placeholder="Batch" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部 Batch</SelectItem>
            {batches.map((batch) => (
              <SelectItem key={batch.batch_id} value={batch.batch_id}>
                {batch.title || batch.batch_id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <SlidersHorizontal className="h-3.5 w-3.5 shrink-0" />
          <span className="shrink-0">推荐分数</span>
          <Input
            className="h-9 w-20"
            min={0}
            max={100}
            type="number"
            value={filters.minScore}
            onChange={(event) => set("minScore", clampScore(event.target.value, 0))}
          />
          <span className="shrink-0">到</span>
          <Input
            className="h-9 w-20"
            min={0}
            max={100}
            type="number"
            value={filters.maxScore}
            onChange={(event) => set("maxScore", clampScore(event.target.value, 100))}
          />
        </div>

        <div className="flex justify-end">
          <Button className="h-9" size="sm" variant="outline" onClick={onClear}>
            <X className="h-3.5 w-3.5" />
            清空
          </Button>
        </div>
      </div>
    </section>
  );
}

function clampScore(value: string, fallback: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(0, Math.min(100, Math.round(parsed)));
}
