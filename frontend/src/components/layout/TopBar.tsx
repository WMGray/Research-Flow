import React from "react";

export const TopBar: React.FC = () => {
  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-outline-variant/10 bg-surface/90 px-6 py-5 backdrop-blur-xl sm:px-8">
      <div className="flex items-center gap-4 flex-1">
        <div className="min-w-0">
          <h1 className="text-xl font-extrabold tracking-tight text-on-surface">
            Dashboard
          </h1>
          <p className="mt-1 text-[10px] font-bold uppercase tracking-[0.24em] text-on-surface-variant">
            Overview
          </p>
        </div>
        <div className="relative ml-auto hidden w-full max-w-xl md:block">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-base text-on-surface-variant">
            search
          </span>
          <input
            className="w-full rounded-lg border-none bg-surface-container-high py-2 pl-10 pr-4 text-sm outline-none transition-all focus:ring-2 focus:ring-primary/20"
            placeholder="Search research materials..."
            type="text"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          className="flex h-10 w-10 items-center justify-center rounded-lg text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-primary"
          type="button"
        >
          <span className="material-symbols-outlined">notifications</span>
        </button>
        <button
          className="flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-on-primary shadow-sm transition-all hover:bg-primary-dim"
          type="button"
        >
          <span className="material-symbols-outlined text-lg">note_add</span>
          <span className="hidden sm:inline">Quick Note</span>
        </button>
      </div>
    </header>
  );
};
