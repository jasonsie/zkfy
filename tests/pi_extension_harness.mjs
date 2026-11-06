// Drives extensions/zkfy.ts the way Pi would, without Pi: loads it, hands it a fake `pi`, replays
// one write of the note named on the command line and prints what the extension did.
// Run: node tests/pi_extension_harness.mjs <extension.ts> <cwd> <note path>
import { pathToFileURL } from "node:url";

const [, , extension, cwd, note] = process.argv;
const calls = [];
const handlers = {};
const pi = {
  registerMcpServer: (name, config) => calls.push({ mcp: name, config }),
  on: (event, handler) => { handlers[event] = handler; },
};
const mod = await import(pathToFileURL(extension).href);
mod.default(pi);
const ctx = { cwd, sessionManager: { getSessionId: () => "harness" } };
const call = { toolCallId: "1", toolName: "write", input: { path: note, content: "# note\n" } };
const onCall = await handlers.tool_call?.(call, ctx);
const onResult = await handlers.tool_result?.({ toolCallId: "1", toolName: "write", input: call.input, content: [{ type: "text", text: "wrote" }] }, ctx);
console.log(JSON.stringify({ calls, events: Object.keys(handlers).sort(), path: call.input.path, onCall: onCall ?? null, onResult: onResult ?? null }));
