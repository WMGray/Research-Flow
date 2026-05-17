import { useRef } from "react";
import type React from "react";

import { cn } from "@/lib/utils";

type ResizableSplitterProps = {
  ariaLabel: string;
  className?: string;
  onDrag: (deltaX: number) => void;
};

export function ResizableSplitter({ ariaLabel, className, onDrag }: ResizableSplitterProps) {
  const startXRef = useRef(0);

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    startXRef.current = event.clientX;

    const onPointerMove = (moveEvent: PointerEvent) => {
      const nextDelta = moveEvent.clientX - startXRef.current;
      startXRef.current = moveEvent.clientX;
      onDrag(nextDelta);
    };

    const onPointerUp = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  };

  return (
    <div
      aria-label={ariaLabel}
      className={cn("hidden w-1 shrink-0 cursor-col-resize bg-border/60 transition-colors hover:bg-neutral-400 xl:block", className)}
      role="separator"
      tabIndex={0}
      onPointerDown={onPointerDown}
    />
  );
}
