import React from "react";
import { TopBar } from "@/components/layout/TopBar";

export const HomePage: React.FC = () => {
  return (
    <div className="flex min-h-full flex-col">
      <TopBar />
      <main className="flex-1 p-6 sm:p-8">
        <div className="space-y-8 max-w-[1600px] pb-12">
          {/* Top Section: Metric Cards Grid */}
          <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Library Card */}
            <div className="bg-surface-container-lowest p-6 rounded-xl shadow-[0_8px_32px_rgba(45,52,53,0.04)] border border-outline-variant/10">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <p className="text-on-surface-variant text-sm font-medium label-md mb-1">
                    Total papers
                  </p>
                  <h2 className="text-3xl font-extrabold tracking-tighter text-on-background">
                    1,402
                  </h2>
                </div>
                <div className="bg-primary/5 p-2 rounded-lg">
                  <span className="material-symbols-outlined text-primary">
                    library_books
                  </span>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-on-surface-variant">
                    Favorited
                  </span>
                  <div className="flex items-center gap-2 flex-1 mx-4">
                    <div className="h-1 bg-surface-container-high flex-1 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary"
                        style={{ width: "17.1%" }}
                      ></div>
                    </div>
                  </div>
                  <span className="text-xs font-semibold">240</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-on-surface-variant">
                    LLM Analyzed
                  </span>
                  <div className="flex items-center gap-2 flex-1 mx-4">
                    <div className="h-1 bg-surface-container-high flex-1 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-dim"
                        style={{ width: "60.6%" }}
                      ></div>
                    </div>
                  </div>
                  <span className="text-xs font-semibold">850</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-on-surface-variant">
                    Manual Summarized
                  </span>
                  <div className="flex items-center gap-2 flex-1 mx-4">
                    <div className="h-1 bg-surface-container-high flex-1 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-outline-variant"
                        style={{ width: "8.5%" }}
                      ></div>
                    </div>
                  </div>
                  <span className="text-xs font-semibold">120</span>
                </div>
              </div>
            </div>

            {/* Dataset Card */}
            <div className="bg-surface-container-lowest p-6 rounded-xl shadow-[0_8px_32px_rgba(45,52,53,0.04)] border border-outline-variant/10 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-8 opacity-[0.03] group-hover:opacity-[0.05] transition-opacity">
                <span
                  className="material-symbols-outlined text-[120px]"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  database
                </span>
              </div>
              <p className="text-on-surface-variant text-sm font-medium mb-1">
                Total Datasets Collected
              </p>
              <div className="flex items-baseline gap-2 mt-2">
                <h2 className="text-6xl font-black tracking-tighter text-primary">
                  48
                </h2>
                <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded uppercase tracking-widest">
                  Active nodes
                </span>
              </div>
              <div className="mt-8 flex gap-4">
                <button className="bg-primary text-on-primary px-4 py-2 rounded-md text-xs font-bold hover:bg-primary-dim transition-all shadow-sm">
                  Manage Assets
                </button>
                <button className="bg-surface-container-high text-on-surface px-4 py-2 rounded-md text-xs font-bold hover:bg-surface-container-highest transition-all">
                  Ingest New
                </button>
              </div>
            </div>

            {/* Views Card */}
            <div className="bg-surface-container-lowest p-6 rounded-xl shadow-[0_8px_32px_rgba(45,52,53,0.04)] border border-outline-variant/10 flex">
              <div className="flex-1">
                <p className="text-on-surface-variant text-sm font-medium mb-1">
                  Total Views
                </p>
                <h2 className="text-3xl font-extrabold tracking-tighter text-on-background mb-6">
                  3,205
                </h2>
                <ul className="space-y-2">
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-primary"></span>
                    <span className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider">
                      Background
                    </span>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-300"></span>
                    <span className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider">
                      Method
                    </span>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-gray-300"></span>
                    <span className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider">
                      Limitation
                    </span>
                  </li>
                </ul>
              </div>
              <div className="flex-shrink-0 flex items-center justify-center p-4">
                <div className="relative w-28 h-28">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      className="text-gray-200"
                      cx="56"
                      cy="56"
                      fill="transparent"
                      r="48"
                      stroke="currentColor"
                      strokeWidth="12"
                    ></circle>
                    <circle
                      className="text-primary"
                      cx="56"
                      cy="56"
                      fill="transparent"
                      r="48"
                      stroke="currentColor"
                      strokeDasharray="301"
                      strokeDashoffset="120"
                      strokeWidth="12"
                    ></circle>
                    <circle
                      className="text-blue-300"
                      cx="56"
                      cy="56"
                      fill="transparent"
                      r="48"
                      stroke="currentColor"
                      strokeDasharray="301"
                      strokeDashoffset="240"
                      strokeWidth="12"
                    ></circle>
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="material-symbols-outlined text-on-surface-variant/30">
                      analytics
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Bottom Section: Split 70/30 */}
          <section className="grid grid-cols-10 gap-6">
            {/* Left Panel (70%): Submission Timeline */}
            <div className="col-span-10 lg:col-span-7 bg-surface-container-lowest p-8 rounded-xl shadow-[0_8px_32px_rgba(45,52,53,0.04)] border border-outline-variant/10">
              <div className="flex justify-between items-end mb-8">
                <div>
                  <h3 className="text-2xl font-bold tracking-tight text-on-background">
                    Submission Timeline
                  </h3>
                  <p className="text-on-surface-variant text-sm">
                    Upcoming major venue deadlines and status monitoring.
                  </p>
                </div>
                <button className="text-primary text-sm font-bold flex items-center hover:underline">
                  View Full Calendar{" "}
                  <span className="material-symbols-outlined text-sm ml-1">
                    arrow_forward
                  </span>
                </button>
              </div>

              <div className="space-y-4">
                {/* Conference Item 1 */}
                <div className="flex items-center p-5 rounded-lg hover:bg-surface-container-low transition-colors border-l-4 border-primary">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <span className="font-black text-xl text-on-background tracking-tighter">
                        CVPR 2026
                      </span>
                      <span className="text-[10px] bg-surface-container-high text-on-surface-variant px-2 py-0.5 rounded font-bold uppercase tracking-widest border border-outline-variant/20">
                        CCF-A
                      </span>
                    </div>
                    <div className="flex gap-8 mt-2 text-xs text-on-surface-variant font-medium">
                      <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px]">
                          event
                        </span>{" "}
                        Abstract: Nov 15, 2025
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px]">
                          history_edu
                        </span>{" "}
                        Full: Nov 22, 2025
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-primary text-lg font-extrabold tracking-tight">
                      45 Days Left
                    </span>
                    <span className="text-[10px] font-bold text-on-surface-variant uppercase">
                      Critical Window
                    </span>
                  </div>
                </div>

                {/* Conference Item 2 */}
                <div className="flex items-center p-5 rounded-lg hover:bg-surface-container-low transition-colors border-l-4 border-outline-variant">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <span className="font-black text-xl text-on-background tracking-tighter">
                        ICML 2026
                      </span>
                      <span className="text-[10px] bg-surface-container-high text-on-surface-variant px-2 py-0.5 rounded font-bold uppercase tracking-widest border border-outline-variant/20">
                        CCF-A
                      </span>
                    </div>
                    <div className="flex gap-8 mt-2 text-xs text-on-surface-variant font-medium">
                      <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px]">
                          event
                        </span>{" "}
                        Abstract: Jan 10, 2026
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px]">
                          history_edu
                        </span>{" "}
                        Full: Jan 17, 2026
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-on-background text-lg font-bold tracking-tight">
                      102 Days Left
                    </span>
                    <span className="text-[10px] font-bold text-on-surface-variant uppercase">
                      Planning Stage
                    </span>
                  </div>
                </div>

                {/* Conference Item 3 */}
                <div className="flex items-center p-5 rounded-lg hover:bg-surface-container-low transition-colors border-l-4 border-blue-300 bg-surface-container-low/30 opacity-75">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <span className="font-black text-xl text-on-background tracking-tighter">
                        AAAI 2026
                      </span>
                      <span className="text-[10px] bg-surface-container-high text-on-surface-variant px-2 py-0.5 rounded font-bold uppercase tracking-widest border border-outline-variant/20">
                        CCF-A
                      </span>
                    </div>
                    <div className="flex gap-8 mt-2 text-xs text-on-surface-variant font-medium">
                      <span className="flex items-center gap-1 line-through opacity-50">
                        Abstract: Aug 15, 2025
                      </span>
                      <span className="flex items-center gap-1 line-through opacity-50">
                        Full: Aug 22, 2025
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-primary-dim text-xs font-black uppercase tracking-widest px-3 py-1 bg-primary/10 rounded-full">
                      Submitted
                    </span>
                    <span className="text-[10px] font-bold text-on-surface-variant uppercase mt-1">
                      Ref ID: 4122
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Panel (30%): Status & Monitor */}
            <div className="col-span-10 lg:col-span-3 space-y-6">
              {/* Recent Activity */}
              <div className="bg-surface-container-lowest p-6 rounded-xl shadow-[0_8px_32px_rgba(45,52,53,0.04)] border border-outline-variant/10 h-[380px] flex flex-col">
                <div className="flex items-center gap-2 mb-6">
                  <span className="material-symbols-outlined text-primary text-lg">
                    history
                  </span>
                  <h4 className="text-sm font-bold uppercase tracking-widest text-on-surface-variant">
                    Recent Activity
                  </h4>
                </div>
                <div className="flex-1 space-y-4 overflow-y-auto pr-2 custom-scrollbar">
                  <div className="flex gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0"></div>
                    <div>
                      <p className="text-xs font-semibold text-on-background">
                        Added paper:{" "}
                        <span className="text-primary italic">
                          "Video Mamba: State Space Model for Video..."
                        </span>
                      </p>
                      <span className="text-[10px] text-on-surface-variant">
                        2 mins ago • Library
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0"></div>
                    <div>
                      <p className="text-xs font-semibold text-on-background">
                        Extracted views from{" "}
                        <span className="text-primary">[Ref 42]</span>
                      </p>
                      <span className="text-[10px] text-on-surface-variant">
                        14 mins ago • Analyzer
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0"></div>
                    <div>
                      <p className="text-xs font-semibold text-on-background">
                        Dataset 'ImageNet-V2' updated
                      </p>
                      <span className="text-[10px] text-on-surface-variant">
                        1 hour ago • Datasets
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* LLM Connectivity */}
              <div className="bg-surface-container-lowest p-6 rounded-xl shadow-[0_8px_32px_rgba(45,52,53,0.04)] border border-outline-variant/10">
                <div className="flex items-center gap-2 mb-6">
                  <span className="material-symbols-outlined text-primary text-lg">
                    router
                  </span>
                  <h4 className="text-sm font-bold uppercase tracking-widest text-on-surface-variant">
                    LLM Connectivity
                  </h4>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-on-surface">
                      OpenAI GPT-4o
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold text-on-surface-variant">
                        42ms
                      </span>
                      <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]"></div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-on-surface">
                      Claude 3.5 Sonnet
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold text-on-surface-variant">
                        58ms
                      </span>
                      <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]"></div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-on-surface">
                      Gemini 1.5 Pro
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold text-primary animate-pulse italic">
                        Connecting...
                      </span>
                      <div className="w-2 h-2 rounded-full bg-amber-400"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};
