import { Plus, X } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import type { PaperRecord, ResearchLogRecord } from "@/lib/api";

type ResearchLogTimelineProps = {
  paper: PaperRecord;
  logs: ResearchLogRecord[];
  onCreateLog: () => void;
  onSaveLog?: (log: ResearchLogRecord) => void;
};

export function ResearchLogTimeline({ logs, onCreateLog, onSaveLog, paper }: ResearchLogTimelineProps) {
  void paper;

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <SectionHeading title="研究日志" subtitle="按时间记录阅读判断、任务和后续动作。" />
        <Button className="h-7 px-2 text-xs" size="sm" variant="outline" onClick={onCreateLog}>
          <Plus className="h-3.5 w-3.5" />
          新建日志
        </Button>
      </div>

      <div className="space-y-3">
        {logs.length > 0 ? logs.map((log) => (
          <ResearchLogCard key={log.id} log={log} onSave={onSaveLog} />
        )) : <p className="text-xs leading-5 text-slate-500">暂无研究日志。</p>}
      </div>
    </section>
  );
}

export function ResearchLogCard({ compact = false, log, onSave }: { log: ResearchLogRecord; compact?: boolean; onSave?: (log: ResearchLogRecord) => void }) {
  const [title, setTitle] = useState(log.title);
  const [bullets, setBullets] = useState(log.bullets);
  const [steps, setSteps] = useState(
    log.next_steps.map((label, index) => ({
      checked: log.tasks[index]?.checked ?? index === 0,
      id: log.tasks[index]?.id ?? `${log.id}-step-${index}`,
      label,
    })),
  );

  useEffect(() => {
    setTitle(log.title);
    setBullets(log.bullets);
    setSteps(
      log.next_steps.map((label, index) => ({
        checked: log.tasks[index]?.checked ?? index === 0,
        id: log.tasks[index]?.id ?? `${log.id}-step-${index}`,
        label,
      })),
    );
  }, [log]);

  const updateBullet = (index: number, value: string) => {
    setBullets((current) => current.map((bullet, itemIndex) => (itemIndex === index ? value : bullet)));
  };

  const addBullet = () => {
    setBullets((current) => [...current, "新增记录"]);
  };

  const removeBullet = (index: number) => {
    setBullets((current) => current.filter((_, itemIndex) => itemIndex !== index));
  };

  const updateStep = (index: number, value: string) => {
    setSteps((current) => current.map((step, itemIndex) => (itemIndex === index ? { ...step, label: value } : step)));
  };

  const toggleStep = (index: number) => {
    setSteps((current) => current.map((step, itemIndex) => (itemIndex === index ? { ...step, checked: !step.checked } : step)));
  };

  const addStep = () => {
    setSteps((current) => [...current, { checked: false, id: `${log.id}-step-${Date.now()}`, label: "新增步骤" }]);
  };

  const removeStep = (index: number) => {
    setSteps((current) => current.filter((_, itemIndex) => itemIndex !== index));
  };

  const save = () => {
    onSave?.({
      ...log,
      title,
      bullets,
      next_steps: steps.map((step) => step.label),
      tasks: steps,
    });
  };

  return (
    <article className="border-l-2 border-blue-200 pl-3">
      <div className="flex items-baseline justify-between gap-2">
        <input
          className="min-w-0 flex-1 rounded border-transparent bg-transparent px-1 py-0.5 text-xs font-semibold text-slate-800 outline-none hover:border-slate-200 focus:border-blue-200 focus:bg-white"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <time className="shrink-0 text-[11px] text-slate-500">{log.timestamp}</time>
      </div>
      <ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">
        {bullets.map((bullet, index) => (
          <li className="flex items-start gap-2" key={`${log.id}-bullet-${index}`}>
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-slate-400" />
            <input
              className="min-w-0 flex-1 rounded border-transparent bg-transparent px-1 py-0.5 text-xs leading-5 text-slate-600 outline-none hover:border-slate-200 focus:border-blue-200 focus:bg-white"
              value={bullet}
              onChange={(event) => updateBullet(index, event.target.value)}
            />
            <button className="mt-0.5 grid h-5 w-5 place-items-center rounded text-slate-300 hover:bg-slate-100 hover:text-red-500" type="button" onClick={() => removeBullet(index)}>
              <X className="h-3 w-3" />
            </button>
          </li>
        ))}
      </ul>
      {!compact ? (
        <button className="mt-2 inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-blue-600" type="button" onClick={addBullet}>
          <Plus className="h-3 w-3" />
          添加记录
        </button>
      ) : null}
      <div className="mt-2 rounded border bg-slate-50 px-2 py-2">
        <div className="flex items-center justify-between gap-2">
          <div className="text-[11px] font-semibold uppercase text-slate-500">Next Steps</div>
          {!compact ? (
            <button className="inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-blue-600" type="button" onClick={addStep}>
              <Plus className="h-3 w-3" />
              添加
            </button>
          ) : null}
        </div>
        <div className="mt-1 space-y-1 text-xs text-slate-700">
          {steps.map((step, index) => (
            <label className="flex items-center gap-2" key={step.id}>
              <input checked={step.checked} className="h-3.5 w-3.5 rounded border-slate-300" type="checkbox" onChange={() => toggleStep(index)} />
              <input
                className="min-w-0 flex-1 rounded border-transparent bg-transparent px-1 py-0.5 text-xs text-slate-700 outline-none hover:border-slate-200 focus:border-blue-200 focus:bg-white"
                value={step.label}
                onChange={(event) => updateStep(index, event.target.value)}
              />
              {!compact ? (
                <button className="grid h-5 w-5 place-items-center rounded text-slate-300 hover:bg-slate-100 hover:text-red-500" type="button" onClick={() => removeStep(index)}>
                  <X className="h-3 w-3" />
                </button>
              ) : null}
            </label>
          ))}
        </div>
      </div>
      {!compact && onSave ? (
        <Button className="mt-2 h-7 px-2 text-xs" size="sm" variant="outline" onClick={save}>
          保存日志
        </Button>
      ) : null}
    </article>
  );
}

function SectionHeading({ subtitle, title }: { title: string; subtitle?: string }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      {subtitle ? <p className="text-xs text-slate-500">{subtitle}</p> : null}
    </div>
  );
}
