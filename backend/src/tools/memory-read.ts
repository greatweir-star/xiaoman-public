import { readJson } from "../memory/store.js";

export function createMemoryReadTool(): any {
  return {
    name: "memory_read",
    description: "读取小满记忆中关于用户的信息",
    parameters: {
      type: "object",
      properties: {
        namespace: {
          type: "string",
          enum: ["identity", "workflow", "voice", "instruction"],
          description: "记忆命名空间",
        },
        key: { type: "string", description: "记忆键名" },
      },
      required: ["namespace", "key"],
    },
    execute: async (_toolCallId: string, params: { namespace: string; key: string }) => {
      const memory = (await readJson(`memory/${params.namespace}.json`)) as Record<string, any>;
      return memory[params.key] ?? null;
    },
  };
}
