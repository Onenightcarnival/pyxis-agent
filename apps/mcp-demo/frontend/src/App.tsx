import { useCallback, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { Inventory } from "./components/Inventory";
import { StepCard } from "./components/StepCard";
import { fetchInventory, streamRun } from "./sse";
import type { AgentStep, ToolDescriptor } from "./types";

export default function App() {
  const [tools, setTools] = useState<ToolDescriptor[]>([]);
  const [question, setQuestion] = useState(
    "把 'pyxis is declarative' 反转，再数一下它的单词数。",
  );
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 空闲时就把工具清单拉回来——让左栏第一眼就有内容
  useEffect(() => {
    fetchInventory()
      .then(setTools)
      .catch((e) => setError(`工具清单加载失败：${e}`));
  }, []);

  const run = useCallback(async () => {
    if (!question.trim() || busy) return;
    setSteps([]);
    setAnswer(null);
    setError(null);
    setBusy(true);

    const ac = new AbortController();
    abortRef.current = ac;

    try {
      for await (const frame of streamRun(question, ac.signal)) {
        if (frame.kind === "inventory") {
          flushSync(() => setTools(frame.tools));
        } else if (frame.kind === "step") {
          const step: AgentStep = {
            index: frame.index,
            thought: frame.thought,
            action: frame.action,
            observation: frame.observation,
          };
          flushSync(() => {
            setSteps((prev) => [...prev, step]);
            setActiveTool(frame.action.name);
          });
        } else if (frame.kind === "done") {
          flushSync(() => {
            setAnswer(frame.answer);
            setActiveTool(null);
          });
        } else if (frame.kind === "error") {
          flushSync(() => setError(frame.message));
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError(String(e));
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }, [question, busy]);

  const stop = () => abortRef.current?.abort();
  const reset = () => {
    abortRef.current?.abort();
    setSteps([]);
    setAnswer(null);
    setError(null);
    setActiveTool(null);
  };

  return (
    <div className="flex h-full">
      <Inventory tools={tools} activeToolName={activeTool} />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-zinc-200 bg-white px-6 py-3 shadow-sm">
          <div>
            <div className="text-sm font-semibold text-zinc-900">
              pyxis mcp-demo
            </div>
            <div className="text-xs text-zinc-500">
              native Tool + MCP server 混合注册，agent loop 对来源无感
            </div>
          </div>
          <button
            onClick={reset}
            disabled={busy}
            className="rounded-md border border-zinc-200 bg-white px-3 py-1 text-sm text-zinc-600 hover:bg-zinc-50 disabled:opacity-40"
          >
            清空
          </button>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-3 p-4">
            {steps.length === 0 && !error && (
              <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-6 text-sm text-zinc-500">
                <div className="font-semibold text-zinc-700">
                  提几个可以让 agent 混用工具的问题：
                </div>
                <ul className="mt-2 space-y-1 list-disc pl-5">
                  <li>"(17 * 23) + 41 等于多少？"（只用 native calculate）</li>
                  <li>"把 'hello' 反转再转大写"（只用 MCP 工具）</li>
                  <li>"当前时间的字符数是多少？"（MCP now → native calculate 兜不住，
                    但可以 upper + 数字符；观察 agent 怎么选）</li>
                </ul>
              </div>
            )}

            {steps.map((s) => (
              <StepCard key={s.index} step={s} />
            ))}

            {answer !== null && (
              <div className="step-enter rounded-xl border-2 border-zinc-900 bg-white p-4 shadow-md">
                <div className="text-xs font-mono uppercase tracking-wide text-zinc-400">
                  final answer
                </div>
                <div className="mt-1 whitespace-pre-wrap text-base text-zinc-900">
                  {answer}
                </div>
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-red-300 bg-red-50 p-3 text-sm text-red-700">
                {error}
              </div>
            )}
          </div>
        </main>

        <footer className="border-t border-zinc-200 bg-white p-3">
          <div className="mx-auto flex w-full max-w-3xl items-end gap-2">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={2}
              placeholder="问一个能让 agent 挑工具的问题"
              className="flex-1 resize-none rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm focus:border-zinc-900 focus:outline-none"
              disabled={busy}
            />
            {busy ? (
              <button
                onClick={stop}
                className="h-10 rounded-lg border border-red-300 bg-white px-4 text-sm text-red-600 hover:bg-red-50"
              >
                停止
              </button>
            ) : (
              <button
                onClick={run}
                disabled={!question.trim()}
                className="h-10 rounded-lg bg-zinc-900 px-4 text-sm text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
              >
                跑一次
              </button>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
}
