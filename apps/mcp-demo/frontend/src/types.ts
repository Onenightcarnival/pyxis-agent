// 镜像后端推过来的 SSE 帧。前端只管消费。

export interface ToolField {
  name: string;
  type: string;
  description: string;
  required: boolean;
}

export interface ToolDescriptor {
  name: string;
  /** "native" 或 "mcp:<server_name>" —— 可视化就靠它区分来源 */
  source: string;
  description: string;
  fields: ToolField[];
}

export interface StepAction {
  name: string;
  args: Record<string, unknown>;
  source: string;
}

export interface AgentStep {
  index: number;
  thought: string;
  action: StepAction;
  observation: string;
}

export type SseFrame =
  | { kind: "inventory"; tools: ToolDescriptor[] }
  | {
      kind: "step";
      index: number;
      thought: string;
      action: StepAction;
      observation: string;
    }
  | { kind: "done"; answer: string }
  | { kind: "error"; message: string };
