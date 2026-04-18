import { useCallback, useRef, useState } from "react";
import { ChatView } from "./components/ChatView";
import { InspectView } from "./components/InspectView";
import { ViewToggle } from "./components/ViewToggle";
import { streamChat } from "./sse";
import type { ChatMessage, Turn } from "./types";

export type ViewMode = "chat" | "inspect";

export default function App() {
  const [view, setView] = useState<ViewMode>("chat");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
    };
    const assistantId = crypto.randomUUID();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      reply: { thought: null, response: null },
      streaming: true,
    };

    // 把历史打平给后端（chat 风格的 {role, content}）。注意 assistant 的
    // content 只用自然语言字段（response），不带 thought——和 UI 展示
    // 同构。
    const historyForServer: Turn[] = messages.map((m) => ({
      role: m.role,
      content: m.role === "user" ? m.content : (m.reply?.response ?? ""),
    }));

    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    const ac = new AbortController();
    abortRef.current = ac;

    try {
      for await (const frame of streamChat(text, historyForServer, ac.signal)) {
        if (frame.kind === "partial") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    reply: {
                      thought: frame.thought,
                      response: frame.response,
                    },
                    content: frame.response ?? "",
                  }
                : m,
            ),
          );
        } else if (frame.kind === "done") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    reply: frame.final,
                    content: frame.final.response ?? "",
                    streaming: false,
                  }
                : m,
            ),
          );
        } else if (frame.kind === "error") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, streaming: false, error: frame.message }
                : m,
            ),
          );
        }
      }
    } catch (e) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, streaming: false, error: String(e) }
            : m,
        ),
      );
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }, [input, busy, messages]);

  const stop = () => abortRef.current?.abort();
  const reset = () => {
    abortRef.current?.abort();
    setMessages([]);
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-zinc-200 bg-white px-6 py-3 shadow-sm">
        <div>
          <div className="text-sm font-semibold text-zinc-900">
            pyxis chat-demo
          </div>
          <div className="text-xs text-zinc-500">
            同一份后端流式数据，两种前端渲染 · 切换开关在右
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={reset}
            className="rounded-md border border-zinc-200 bg-white px-3 py-1 text-sm text-zinc-600 hover:bg-zinc-50"
          >
            清空
          </button>
          <ViewToggle value={view} onChange={setView} />
        </div>
      </header>

      <main className="flex-1 overflow-y-auto">
        {view === "chat" ? (
          <ChatView messages={messages} />
        ) : (
          <InspectView messages={messages} />
        )}
      </main>

      <footer className="border-t border-zinc-200 bg-white p-3">
        <div className="mx-auto flex w-full max-w-3xl items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            rows={2}
            placeholder="输入消息，Enter 发送 / Shift+Enter 换行"
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
              onClick={send}
              disabled={!input.trim()}
              className="h-10 rounded-lg bg-zinc-900 px-4 text-sm text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              发送
            </button>
          )}
        </div>
      </footer>
    </div>
  );
}
