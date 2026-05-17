import { Save, X } from "lucide-react";
import { useEffect, useState } from "react";

import { PathCell } from "@/components/common/PathCell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { PaperRecord } from "@/lib/api";
import { getClassificationChoices, type ClassificationOptionSet } from "@/lib/libraryView";

export type EditableMetadataValue = {
  title: string;
  venue: string;
  year: string;
  domain: string;
  area: string;
  topic: string;
  tags: string;
  status: string;
  paper_path: string;
  note_path: string;
  refined_path: string;
};

type EditableMetadataProps = {
  paper: PaperRecord;
  compact?: boolean;
  classificationOptions?: ClassificationOptionSet;
  onSave?: (value: EditableMetadataValue) => Promise<void> | void;
};

export function EditableMetadata({ classificationOptions, compact = false, onSave, paper }: EditableMetadataProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(() => toDraft(paper));
  const choices = classificationOptions ? getClassificationChoices(classificationOptions, draft) : null;

  useEffect(() => {
    setDraft(toDraft(paper));
    setEditing(false);
  }, [paper.paper_id]);

  const save = async () => {
    await onSave?.(draft);
    setEditing(false);
  };

  if (!editing) {
    return (
      <div className="grid gap-1">
        <MetaRow label="Title" value={paper.title} />
        <MetaRow label="Venue" value={paper.venue || "未填写"} />
        <MetaRow label="Year" value={paper.year ? String(paper.year) : "未填写"} />
        <MetaRow label="Domain" value={paper.domain || "未填写"} />
        <MetaRow label="Area" value={paper.area || "未填写"} />
        <MetaRow label="Topic" value={paper.topic || "未填写"} />
        <MetaRow label="Tags" value={paper.tags.length > 0 ? paper.tags.join(", ") : "未填写"} />
        {!compact ? (
          <>
            <MetaRow label="Status" value={paper.status || paper.review_status || "未填写"} />
            <PathMetaRow label="PDF Path" value={paper.paper_path} />
            <PathMetaRow label="Note Path" value={paper.note_path} />
            <PathMetaRow label="Refined Path" value={paper.refined_path || paper.parser_artifacts.refined_path} />
          </>
        ) : null}
        <div className="pt-2">
          <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
            编辑
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-2">
      <Field label="Title" value={draft.title} onChange={(value) => setDraft({ ...draft, title: value })} />
      <Field label="Venue" value={draft.venue} onChange={(value) => setDraft({ ...draft, venue: value })} />
      <Field label="Year" value={draft.year} onChange={(value) => setDraft({ ...draft, year: value })} />
      {choices && choices.domains.length > 0 ? (
        <OptionField
          label="Domain"
          value={draft.domain}
          values={choices.domains}
          onChange={(value) => setDraft({ ...draft, domain: value, area: "", topic: "" })}
        />
      ) : (
        <Field label="Domain" value={draft.domain} onChange={(value) => setDraft({ ...draft, domain: value })} />
      )}
      {choices && choices.areas.length > 0 ? (
        <OptionField
          label="Area"
          value={draft.area}
          values={choices.areas}
          onChange={(value) => setDraft({ ...draft, area: value, topic: "" })}
        />
      ) : (
        <Field label="Area" value={draft.area} onChange={(value) => setDraft({ ...draft, area: value })} />
      )}
      {choices && choices.topics.length > 0 ? (
        <OptionField label="Topic" value={draft.topic} values={choices.topics} onChange={(value) => setDraft({ ...draft, topic: value })} />
      ) : (
        <Field label="Topic" value={draft.topic} onChange={(value) => setDraft({ ...draft, topic: value })} />
      )}
      <Field label="Tags" value={draft.tags} onChange={(value) => setDraft({ ...draft, tags: value })} />
      {!compact ? (
        <>
          <Field label="Status" value={draft.status} onChange={(value) => setDraft({ ...draft, status: value })} />
          <Field label="PDF Path" value={draft.paper_path} onChange={(value) => setDraft({ ...draft, paper_path: value })} />
          <Field label="Note Path" value={draft.note_path} onChange={(value) => setDraft({ ...draft, note_path: value })} />
          <Field label="Refined Path" value={draft.refined_path} onChange={(value) => setDraft({ ...draft, refined_path: value })} />
        </>
      ) : null}
      <div className="flex gap-2 pt-2">
        <Button size="sm" onClick={save}>
          <Save className="h-3.5 w-3.5" />
          Save
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setDraft(toDraft(paper));
            setEditing(false);
          }}
        >
          <X className="h-3.5 w-3.5" />
          Cancel
        </Button>
      </div>
      <p className="text-xs leading-5 text-muted-foreground">保存后会刷新当前论文；分类变更导致文件夹移动时，详情会自动切到新的路径。</p>
    </div>
  );
}

function Field({ label, onChange, value }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Input className="h-8" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function OptionField({ label, onChange, value, values }: { label: string; value: string; values: string[]; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <Select value={value || "none"} onValueChange={(nextValue) => onChange(nextValue === "none" ? "" : nextValue)}>
        <SelectTrigger className="h-8">
          <SelectValue placeholder={`选择 ${label}`} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="none">未填写</SelectItem>
          {values.map((item) => (
            <SelectItem key={item} value={item}>
              {item}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </label>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[92px_minmax(0,1fr)] gap-3 border-t py-2 first:border-t-0 first:pt-0 last:pb-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="min-w-0 truncate text-xs font-medium" title={value}>
        {value || "未填写"}
      </span>
    </div>
  );
}

function PathMetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[92px_minmax(0,1fr)] gap-3 border-t py-2 first:border-t-0 first:pt-0 last:pb-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <PathCell value={value} />
    </div>
  );
}

function toDraft(paper: PaperRecord): EditableMetadataValue {
  return {
    title: paper.title,
    venue: paper.venue,
    year: paper.year ? String(paper.year) : "",
    domain: paper.domain,
    area: paper.area,
    topic: paper.topic,
    tags: paper.tags.join(", "),
    status: paper.status,
    paper_path: paper.paper_path,
    note_path: paper.note_path,
    refined_path: paper.refined_path || paper.parser_artifacts.refined_path,
  };
}
