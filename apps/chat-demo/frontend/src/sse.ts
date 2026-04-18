import type { SseFrame, Turn } from "./types";

/**
 * 对后端 /chat 端点发 POST，拿 ReadableStream 回来，
 * 手动解析 SSE（`data: ...\n\n` 分隔），每帧 yield 一次。
 *
 * 没用 EventSource：后者只支持 GET，不方便传 history body。
 */
export async function* streamChat(
  message: string,
  history: Turn[],
  signal?: AbortSignal,
): AsyncGenerator<SseFrame> {
  const resp = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
    signal,
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`HTTP ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE 事件以空行分隔
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);

      // 支持多行 data: 前缀的 SSE，这里最朴素处理
      const dataLine = raw
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim())
        .join("");
      if (!dataLine) continue;
      try {
        yield JSON.parse(dataLine) as SseFrame;
      } catch (e) {
        // 忽略解析错误的帧
        console.warn("bad SSE frame:", dataLine, e);
      }
    }
  }
}
