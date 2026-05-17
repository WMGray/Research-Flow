import { Download } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useDialog } from "@/components/ui/DialogProvider";
import { Input } from "@/components/ui/input";
import { importPaper } from "@/lib/api";

export function TopBar() {
  const { notify } = useDialog();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-end gap-3 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <Button
        className="gap-2"
        size="sm"
        onClick={() => setOpen(true)}
      >
        <Download className="h-4 w-4" />
        <span>Import Paper</span>
      </Button>
      <ImportPaperDialog
        open={open}
        onOpenChange={setOpen}
        onImported={(title) =>
          notify({
            title: "论文已导入",
            message: title,
          })
        }
      />
    </header>
  );
}

function ImportPaperDialog({
  onImported,
  onOpenChange,
  open,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImported: (title: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [source, setSource] = useState("");
  const [authors, setAuthors] = useState("");
  const [venue, setVenue] = useState("");
  const [year, setYear] = useState("");
  const [refresh, setRefresh] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    const cleanTitle = title.trim();
    if (!cleanTitle) {
      setError("Title 必填。");
      return;
    }
    setSubmitting(true);
    try {
      const response = await importPaper({
        title: cleanTitle,
        source: source.trim() || undefined,
        authors: authors.split(",").map((item) => item.trim()).filter(Boolean),
        venue: venue.trim(),
        year: year ? Number(year) : null,
        refresh_metadata: refresh,
      });
      setTitle("");
      setSource("");
      setAuthors("");
      setVenue("");
      setYear("");
      setRefresh(true);
      setError("");
      onOpenChange(false);
      onImported(response.data.title);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import Paper</DialogTitle>
          <DialogDescription>Title 必填，本地 PDF 或目录路径可选；导入后可以立即刷新元数据。</DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div> : null}
          <Input autoFocus placeholder="Title" value={title} onChange={(event) => setTitle(event.target.value)} />
          <Input placeholder="本地 PDF 或论文目录路径（可选）" value={source} onChange={(event) => setSource(event.target.value)} />
          <Input placeholder="Authors，用英文逗号分隔（可选）" value={authors} onChange={(event) => setAuthors(event.target.value)} />
          <div className="grid grid-cols-2 gap-2">
            <Input placeholder="Venue（可选）" value={venue} onChange={(event) => setVenue(event.target.value)} />
            <Input placeholder="Year（可选）" type="number" value={year} onChange={(event) => setYear(event.target.value)} />
          </div>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input checked={refresh} className="h-4 w-4" type="checkbox" onChange={(event) => setRefresh(event.target.checked)} />
            导入后刷新元数据
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button disabled={submitting} onClick={() => void submit()}>
            {submitting ? "导入中" : "导入"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
