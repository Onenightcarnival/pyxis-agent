import type { ChatMessage } from "../types";

/**
 * 标准 {role, content} 风格的气泡流。
 * 对 assistant 消息，content 取自 reply.response（schema 的自然语言字段）。
 * thought 字段在此视图下**被刻意隐藏**——chat 心智模型里用户不关心中间推理。
 */
export function ChatView({ messages }: { messages: ChatMessage[] }) {
  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-zinc-400">
        发条消息开始对话——顶部的 Chat / Inspect 可以切换两种渲染风格。
      </div>
    );
  }
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-3 p-4">
      {messages.map((m) => (
        <Bubble key={m.id} m={m} />
      ))}
    </div>
  );
}

function Bubble({ m }: { m: ChatMessage }) {
  const isUser = m.role === "user";
  const text = isUser ? m.content : (m.reply?.response ?? "");
  const showTyping = !isUser && m.streaming && !text;
  return (
    <div className={"flex " + (isUser ? "justify-end" : "justify-start")}>
      <div
        className={
          "max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 shadow-sm " +
          (isUser
            ? "bg-zinc-900 text-white"
            : "bg-white text-zinc-900 border border-zinc-200")
        }
      >
        {m.error ? (
          <span className="text-red-600">{m.error}</span>
        ) : showTyping ? (
          <TypingDots />
        ) : (
          text || <span className="text-zinc-400">（空）</span>
        )}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex gap-1">
      <Dot delay="0ms" />
      <Dot delay="150ms" />
      <Dot delay="300ms" />
    </span>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-400"
      style={{ animationDelay: delay }}
    />
  );
}
