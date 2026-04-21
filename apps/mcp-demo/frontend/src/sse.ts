import type { SseFrame, ToolDescriptor } from "./types";

export async function fetchInventory(): Promise<ToolDescriptor[]> {
  const resp = await fetch("/api/inventory");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const data = (await resp.json()) as { tools: ToolDescriptor[] };
  return data.tools;
}

/**
 * 对后端 /run 端点发 POST，拿 ReadableStream 回来，手动解析 SSE
 * （`data: ...\n\n` 分隔），每帧 yield 一次。
 */
export async function* streamRun(
  question: string,
  signal?: AbortSignal,
): AsyncGenerator<SseFrame> {
  const resp = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
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

    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);

      const dataLine = raw
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim())
        .join("");
      if (!dataLine) continue;
      try {
        yield JSON.parse(dataLine) as SseFrame;
      } catch (e) {
        console.warn("bad SSE frame:", dataLine, e);
      }
    }
  }
}
