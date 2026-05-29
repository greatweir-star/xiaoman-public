import { readJson, writeJson } from "../memory/store.js";

export function createMemoryWriteTool(): any {
  return {
    name: "memory_write",
    description: "更新小满记忆中关于用户的信息",
    parameters: {
      type: "object",
      properties: {
        namespace: {
          type: "string",
          enum: ["identity", "workflow", "voice", "instruction"],
        },
        key: { type: "string" },
        value: { type: "string" },
      },
      required: ["namespace", "key", "value"],
    },
    execute: async (_toolCallId: string, params: { namespace: string; key: string; value: string }) => {
      const filePath = `memory/${params.namespace}.json`;
      const memory = (await readJson(filePath)) as Record<string, any>;
      memory[params.key] = { value: params.value, updated_at: Date.now() };
      await writeJson(filePath, memory);
      return { success: true };
    },
  };
}
