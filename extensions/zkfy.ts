// Pi extension for zkfy. Pi loads no plugin hooks and no plugin MCP server, so this one file
// plays both: it runs the plugin's two hook scripts around Pi's write and edit tools, in the
// shape Claude Code gives them (tool_name Write|Edit, tool_input.file_path), and registers the
// Notion server that .mcp.json and mcp_config.json name for the other CLIs. Pi loads it from
// extensions/ by convention; the plugin root is one folder up. A failing script never blocks a
// session on its own.
import { spawnSync } from "node:child_process";
import { realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(realpathSync(fileURLToPath(import.meta.url))));
const TOOLS: Record<string, string> = { write: "Write", edit: "Edit" }; // Pi's tools, as Claude Code names them
export const NOTION = { name: "notion", url: "https://mcp.notion.com/mcp" }; // the same server as .mcp.json

function hook(script: string, payload: Record<string, unknown>, cwd: string): Record<string, any> | undefined {
  try {
    const run = spawnSync("bash", [join(root, "hooks", script)], {
      input: JSON.stringify(payload),
      encoding: "utf8",
      timeout: 20_000,
      cwd,
    });
    const out = run.status === 0 ? run.stdout.trim() : "";
    return out ? JSON.parse(out) : undefined;
  } catch {
    return undefined;
  }
}

function notePath(path: unknown): string | undefined {
  return typeof path === "string" && path.endsWith(".md") ? path : undefined;
}

export default function (pi: any) {
  try {
    pi.registerMcpServer(NOTION.name, { url: NOTION.url, description: "Notion pages, for the notion-to-zk skill" });
  } catch {
    // another extension or the user's mcp.json owns the name: theirs wins
  }

  const calls = new Map<string, { tool: string; path: string; said?: string }>();

  pi.on("tool_call", (event: any, ctx: any) => {
    const tool = TOOLS[event.toolName];
    const path = notePath(event.input?.path);
    if (!tool || !path) return;
    const cwd = ctx?.cwd ?? process.cwd();
    const payload = { session_id: ctx?.sessionManager?.getSessionId?.(), cwd, tool_name: tool, tool_input: { file_path: path } };
    const out = hook("validate-zk-structure.sh", payload, cwd)?.hookSpecificOutput;
    const call = { tool, path, said: out?.additionalContext };
    calls.set(event.toolCallId, call);
    if (!out) return;
    if (out.permissionDecision === "deny") {
      calls.delete(event.toolCallId);
      return { block: true, reason: out.permissionDecisionReason ?? "zkfy: blocked by the vault guard" };
    }
    const moved = out.updatedInput?.file_path;
    if (typeof moved === "string" && moved !== path) {
      event.input.path = moved; // Pi: mutate the input in place
      call.path = moved;
    }
  });

  pi.on("tool_result", (event: any, ctx: any) => {
    const call = calls.get(event.toolCallId);
    if (!call) return;
    calls.delete(event.toolCallId);
    const cwd = ctx?.cwd ?? process.cwd();
    const path = notePath(event.input?.path) ?? call.path;
    const payload = { session_id: ctx?.sessionManager?.getSessionId?.(), cwd, tool_name: call.tool, tool_input: { file_path: path } };
    const after = hook("signal-index-update.sh", payload, cwd)?.hookSpecificOutput?.additionalContext;
    const texts = [call.said, after].filter((t): t is string => typeof t === "string" && t.length > 0);
    if (!texts.length) return;
    return { content: [...(event.content ?? []), { type: "text", text: texts.join("\n") }] };
  });
}
