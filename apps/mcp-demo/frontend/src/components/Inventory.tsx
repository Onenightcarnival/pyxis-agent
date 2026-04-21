import type { ToolDescriptor } from "../types";
import { sourceClasses, SourceBadge } from "./SourceBadge";

/**
 * 左侧边栏：把所有工具（native + MCP）展开给用户看。
 * pyxis 的核心卖点可视化——**多源工具进同一个判别式联合**，LLM 看到的
 * 就是这么一张扁平的列表。
 */
export function Inventory({
  tools,
  activeToolName,
}: {
  tools: ToolDescriptor[];
  activeToolName?: string | null;
}) {
  if (tools.length === 0) {
    return (
      <aside className="w-80 shrink-0 border-r border-zinc-200 bg-white p-4 text-sm text-zinc-400">
        正在连接 MCP server + 枚举工具……
      </aside>
    );
  }
  const grouped: Record<string, ToolDescriptor[]> = {};
  for (const t of tools) (grouped[t.source] ??= []).push(t);
  return (
    <aside className="w-80 shrink-0 overflow-y-auto border-r border-zinc-200 bg-white">
      <div className="sticky top-0 z-10 border-b border-zinc-200 bg-white/90 px-4 py-3 backdrop-blur">
        <div className="text-sm font-semibold text-zinc-900">
          工具清单（{tools.length}）
        </div>
        <div className="text-xs text-zinc-500">
          LLM 看到的判别式联合成员——来源不同，调用面完全一致
        </div>
      </div>
      <div className="p-3 space-y-5">
        {Object.entries(grouped).map(([source, items]) => (
          <div key={source}>
            <div className="mb-2 flex items-center gap-2">
              <SourceBadge source={source} />
              <span className="text-xs text-zinc-400">
                {items.length} 个
              </span>
            </div>
            <div className="space-y-2">
              {items.map((t) => (
                <ToolCard
                  key={t.source + ":" + t.name}
                  t={t}
                  active={activeToolName === t.name}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

function ToolCard({
  t,
  active,
}: {
  t: ToolDescriptor;
  active?: boolean;
}) {
  const c = sourceClasses(t.source);
  return (
    <div
      className={
        "rounded-lg border p-2.5 transition " +
        c.border +
        " " +
        (active ? c.bg + " source-pulse" : "bg-white")
      }
    >
      <div className="flex items-center justify-between">
        <code className="text-xs font-mono text-zinc-900">{t.name}</code>
      </div>
      {t.description && (
        <div className="mt-1 text-xs text-zinc-500">{t.description}</div>
      )}
      {t.fields.length > 0 && (
        <ul className="mt-2 space-y-0.5">
          {t.fields.map((f) => (
            <li
              key={f.name}
              className="flex items-baseline gap-1.5 text-[11px] font-mono"
            >
              <span className="text-zinc-600">{f.name}</span>
              <span className="text-zinc-400">:</span>
              <span className="text-zinc-500">{f.type}</span>
              {!f.required && (
                <span className="text-zinc-400 italic">?</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
