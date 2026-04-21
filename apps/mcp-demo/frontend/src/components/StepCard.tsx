import type { AgentStep } from "../types";
import { sourceClasses, SourceBadge } from "./SourceBadge";

/**
 * 单次 agent 迭代的可视化：thought → action → observation。
 * 关键：action 带一个 source badge，让 native / MCP 的不同来源一眼看见；
 * 但除此之外的 UI 形态完全一致——呼应 pyxis 的设计点：agent loop 只有
 * 一行 `d.action.run()`，来源不同但调用面相同。
 */
export function StepCard({ step }: { step: AgentStep }) {
  const c = sourceClasses(step.action.source);
  const argsJson = JSON.stringify(step.action.args, null, 2);
  return (
    <div
      className={
        "step-enter rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"
      }
    >
      <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wide text-zinc-400">
        <span>step #{step.index}</span>
      </div>

      <div className="mt-2">
        <div className="text-[11px] font-mono text-zinc-400">thought</div>
        <div className="mt-0.5 whitespace-pre-wrap text-sm text-zinc-700">
          {step.thought}
        </div>
      </div>

      <div className={"mt-3 rounded-lg border px-3 py-2 " + c.border + " " + c.bg}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <code className="text-sm font-mono text-zinc-900">
              {step.action.name}
            </code>
            <SourceBadge source={step.action.source} />
          </div>
        </div>
        {argsJson !== "{}" && (
          <pre className="mt-1.5 overflow-x-auto rounded bg-white/70 px-2 py-1 text-[11px] font-mono text-zinc-700">
            {argsJson}
          </pre>
        )}
      </div>

      <div className="mt-3">
        <div className="text-[11px] font-mono text-zinc-400">observation</div>
        <div className="mt-0.5 whitespace-pre-wrap rounded bg-zinc-50 px-2 py-1 text-sm text-zinc-800 font-mono">
          {step.observation || <span className="text-zinc-400">（空）</span>}
        </div>
      </div>
    </div>
  );
}
