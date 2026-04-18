import type { ChatMessage, ChatReply } from "../types";

/**
 * 把每条 assistant 消息的 schema 字段逐个展开。
 * 对比 ChatView：chat 风格只看 response；inspect 风格连 thought 一起看，
 * 并且字段是否已填、填了多少都"活"起来——schema-as-CoT 的可视化。
 */
export function InspectView({ messages }: { messages: ChatMessage[] }) {
  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-zinc-400">
        发条消息开始对话——这一视图把 Pydantic schema 的每个字段都展开给你看。
      </div>
    );
  }
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-3 p-4">
      {messages.map((m) => (
        <Card key={m.id} m={m} />
      ))}
    </div>
  );
}

function Card({ m }: { m: ChatMessage }) {
  const isUser = m.role === "user";
  if (isUser) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-white p-3 shadow-sm">
        <div className="mb-1 text-xs font-mono uppercase tracking-wide text-zinc-400">
          role: user
        </div>
        <div className="whitespace-pre-wrap text-sm text-zinc-900">
          {m.content}
        </div>
      </div>
    );
  }
  const reply = m.reply ?? { thought: null, response: null };
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-center justify-between text-xs font-mono uppercase tracking-wide text-zinc-400">
        <span>role: assistant · output: ChatReply</span>
        {m.streaming && (
          <span className="inline-flex items-center gap-1 text-zinc-500">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            streaming
          </span>
        )}
      </div>
      <SchemaField name="thought" filled={!!reply.thought} value={reply.thought} muted />
      <SchemaField name="response" filled={!!reply.response} value={reply.response} />
      {m.error && (
        <div className="mt-2 rounded bg-red-50 p-2 text-xs text-red-700">
          error: {m.error}
        </div>
      )}
    </div>
  );
}

function SchemaField({
  name,
  value,
  filled,
  muted,
}: {
  name: keyof ChatReply | string;
  value: string | null;
  filled: boolean;
  muted?: boolean;
}) {
  return (
    <div
      className={
        "mt-2 rounded border-l-2 pl-3 py-1 transition-colors " +
        (filled
          ? "border-emerald-500 bg-emerald-50/40 field-fill-in"
          : "border-zinc-200 bg-zinc-50")
      }
    >
      <div className="flex items-center gap-2 text-xs font-mono">
        <span className="text-zinc-500">{name}:</span>
        <span
          className={
            filled
              ? "text-emerald-700"
              : "text-zinc-400 italic"
          }
        >
          {filled ? "filled" : "empty"}
        </span>
      </div>
      <div
        className={
          "whitespace-pre-wrap text-sm " +
          (muted ? "text-zinc-500" : "text-zinc-900")
        }
      >
        {value || <span className="text-zinc-300">—</span>}
      </div>
    </div>
  );
}
