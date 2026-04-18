// 镜像后端 ChatReply schema。
// 字段顺序刻意与 Pydantic 一致：thought 先填，response 后填。
export interface ChatReply {
  thought: string | null;
  response: string | null;
}

// 一条消息的内部表示。assistant 消息携带完整的 ChatReply（供 Inspect view 用），
// user 消息只用 content。
export type Role = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string; // user: 用户输入；assistant: reply.response（可能为 null 直到流到该字段）
  reply?: ChatReply; // 仅 assistant 有
  streaming?: boolean; // 当前是否还在流式填充
  error?: string;
}

// SSE 帧的类型（后端约定）。
export type SseFrame =
  | { kind: "partial"; thought: string | null; response: string | null }
  | { kind: "done"; final: ChatReply }
  | { kind: "error"; message: string };

// 历史数据发给后端的格式：后端只接受 {role, content} 的普通对话流。
export interface Turn {
  role: Role;
  content: string;
}
