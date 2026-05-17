import { useEffect, useState } from "react";

import type { PaneLayoutState } from "@/lib/libraryFolders";

const DEFAULT_LAYOUT: PaneLayoutState = {
  treeWidth: 280,
  detailWidth: 390,
};

const LIMITS = {
  treeMin: 220,
  treeMax: 380,
  detailMin: 340,
  detailMax: 520,
};

export function useResizablePaneLayout(storageKey: string) {
  const [layout, setLayout] = useState<PaneLayoutState>(() => {
    if (typeof window === "undefined") {
      return DEFAULT_LAYOUT;
    }
    try {
      const stored = window.localStorage.getItem(storageKey);
      if (!stored) {
        return DEFAULT_LAYOUT;
      }
      const value = JSON.parse(stored) as Partial<PaneLayoutState>;
      return {
        treeWidth: clamp(value.treeWidth ?? DEFAULT_LAYOUT.treeWidth, LIMITS.treeMin, LIMITS.treeMax),
        detailWidth: clamp(value.detailWidth ?? DEFAULT_LAYOUT.detailWidth, LIMITS.detailMin, LIMITS.detailMax),
      };
    } catch {
      return DEFAULT_LAYOUT;
    }
  });

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(layout));
  }, [layout, storageKey]);

  const resizeTree = (deltaX: number) => {
    setLayout((current) => ({
      ...current,
      treeWidth: clamp(current.treeWidth + deltaX, LIMITS.treeMin, LIMITS.treeMax),
    }));
  };

  const resizeDetail = (deltaX: number) => {
    setLayout((current) => ({
      ...current,
      detailWidth: clamp(current.detailWidth - deltaX, LIMITS.detailMin, LIMITS.detailMax),
    }));
  };

  return { layout, resizeDetail, resizeTree };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, Math.round(value)));
}
