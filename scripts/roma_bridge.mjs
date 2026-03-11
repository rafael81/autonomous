import crypto from 'node:crypto';
import process from 'node:process';

import { CodexAgent } from '/Users/user/project/Opus_Aggregator/roma-cli/dist/lib/agent.js';
import { getCodexCredentials } from '/Users/user/project/Opus_Aggregator/roma-cli/dist/lib/auth.js';

const chunks = [];
for await (const chunk of process.stdin) {
  chunks.push(chunk);
}

const payload = JSON.parse(Buffer.concat(chunks).toString('utf-8') || '{}');
const prompt = typeof payload.prompt === 'string' ? payload.prompt : '';
const history = Array.isArray(payload.history) ? payload.history : [];
const model = typeof payload.model === 'string' && payload.model ? payload.model : 'gpt-5.3-codex-spark';
const instructions =
  typeof payload.instructions === 'string' && payload.instructions
    ? payload.instructions
    : 'You are Codex, a coding agent. Reply briefly.';

const emit = (event) => {
  process.stdout.write(`${JSON.stringify(event)}\n`);
};

const { token, accountId } = getCodexCredentials();
if (!token || !accountId) {
  emit({ type: 'error', message: 'Codex credentials not found in ~/.codex/auth.json' });
  process.exit(2);
}

const sessionId = crypto.randomUUID();
emit({ type: 'session_start', session_id: sessionId, model });

const agent = new CodexAgent({
  token,
  accountId,
  model,
  instructions,
  tools: [],
  localTools: {},
  debugLog: () => {},
  useOpenAIWebSearch: false,
});

agent.on('status', (status) => emit({ type: 'status', text: status }));
agent.on('message', (text) => emit({ type: 'assistant_message_delta', text }));
agent.on('toolCall', (toolCall) => emit({ type: 'tool_call', ...toolCall }));
agent.on('toolResult', (toolResult) => emit({ type: 'tool_result', ...toolResult }));
agent.on('error', (message) => emit({ type: 'error', message }));
agent.on('finalize', (message) => emit({ type: 'assistant_message', text: message.content || '', raw: message }));

try {
  await agent.chat(prompt, history);
  emit({ type: 'session_end', ok: true });
} catch (error) {
  emit({ type: 'error', message: error instanceof Error ? error.message : String(error) });
  emit({ type: 'session_end', ok: false });
  process.exit(1);
}
