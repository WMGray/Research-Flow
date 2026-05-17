import { PanelRightOpen } from "lucide-react";

import { PaperDetailContent, PaperDetailPanel, type EditableMetadataValue } from "@/components/papers/PaperDetailPanel";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import type { PaperRecord } from "@/lib/api";
import type { ClassificationOptionSet } from "@/lib/libraryView";

type ResponsivePaperInspectorProps = {
  paper: PaperRecord | null;
  collapsed?: boolean;
  width?: number;
  classificationOptions?: ClassificationOptionSet;
  onToggleCollapsed?: () => void;
  onMetadataSave?: (value: EditableMetadataValue) => Promise<void> | void;
  onGenerateNote?: (paper: PaperRecord) => Promise<void> | void;
  onParsePdf?: (paper: PaperRecord) => Promise<void> | void;
  onOpenFolder?: (paper: PaperRecord) => Promise<void> | void;
};

export function ResponsivePaperInspector({
  classificationOptions,
  collapsed,
  onGenerateNote,
  onMetadataSave,
  onOpenFolder,
  onParsePdf,
  onToggleCollapsed,
  paper,
  width,
}: ResponsivePaperInspectorProps) {
  return (
    <>
      <PaperDetailPanel
        classificationOptions={classificationOptions}
        collapsed={collapsed}
        onGenerateNote={onGenerateNote}
        onMetadataSave={onMetadataSave}
        onOpenFolder={onOpenFolder}
        onParsePdf={onParsePdf}
        onToggleCollapsed={onToggleCollapsed}
        paper={paper}
        width={width}
      />
      <Sheet>
        <SheetTrigger asChild>
          <Button className="fixed bottom-4 right-4 z-40 shadow-sm xl:hidden" size="sm" disabled={!paper}>
            <PanelRightOpen className="h-4 w-4" />
            详情
          </Button>
        </SheetTrigger>
        <SheetContent className="w-[min(420px,92vw)] p-0" side="right">
          <SheetHeader className="sr-only">
            <SheetTitle>Paper Detail</SheetTitle>
          </SheetHeader>
          <PaperDetailContent
            classificationOptions={classificationOptions}
            onGenerateNote={onGenerateNote}
            onMetadataSave={onMetadataSave}
            onOpenFolder={onOpenFolder}
            onParsePdf={onParsePdf}
            paper={paper}
          />
        </SheetContent>
      </Sheet>
    </>
  );
}
