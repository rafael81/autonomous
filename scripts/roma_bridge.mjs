import crypto from 'node:crypto';
import process from 'node:process';
import { spawn } from 'node:child_process';

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
const enableTools = payload.enableTools !== false;
const toolCwd = typeof payload.cwd === 'string' && payload.cwd ? payload.cwd : process.cwd();

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

async function runBashTool(args = {}) {
  const command = typeof args.command === 'string' ? args.command.trim() : '';
  if (!command) {
    return 'Error: command is required.';
  }

  const cwd = typeof args.cwd === 'string' && args.cwd.trim() ? args.cwd.trim() : toolCwd;
  const timeoutMs = Number.isFinite(args.timeout_ms) ? Math.max(500, Math.min(30000, Number(args.timeout_ms))) : 8000;
  const shell = typeof args.shell === 'string' && args.shell.trim() ? args.shell.trim() : '/bin/bash';
  const maxOutputChars = Number.isFinite(args.max_output_chars) ? Math.max(256, Math.min(16000, Number(args.max_output_chars))) : 8000;

  return await new Promise((resolve) => {
    const child = spawn(shell, ['-lc', command], {
      cwd,
      env: { ...process.env },
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill('SIGTERM');
    }, timeoutMs);

    child.stdout?.on('data', (chunk) => {
      if (stdout.length < maxOutputChars) {
        stdout += chunk.toString('utf-8').slice(0, maxOutputChars - stdout.length);
      }
    });
    child.stderr?.on('data', (chunk) => {
      if (stderr.length < maxOutputChars) {
        stderr += chunk.toString('utf-8').slice(0, maxOutputChars - stderr.length);
      }
    });
    child.on('close', (code, signal) => {
      clearTimeout(timer);
      resolve(
        [
          `command: ${command}`,
          `cwd: ${cwd}`,
          `exit_code: ${code ?? 'n/a'}`,
          `signal: ${signal ?? 'none'}`,
          `timed_out: ${timedOut}`,
          '',
          'stdout:',
          stdout || '(empty)',
          '',
          'stderr:',
          stderr || '(empty)',
        ].join('\n')
      );
    });
    child.on('error', (error) => {
      clearTimeout(timer);
      resolve(`Error: ${error instanceof Error ? error.message : String(error)}`);
    });
  });
}

const toolSpecs = enableTools
  ? [
      {
        type: 'function',
        name: 'bash',
        description: 'Run shell commands to inspect the local workspace and gather evidence.',
        parameters: {
          type: 'object',
          required: ['command'],
          properties: {
            command: { type: 'string', description: 'Shell command to execute.' },
            cwd: { type: 'string', description: 'Working directory.' },
            timeout_ms: { type: 'number', description: 'Command timeout in milliseconds.' },
            max_output_chars: { type: 'number', description: 'Maximum number of output characters to keep.' },
            shell: { type: 'string', description: 'Shell binary to use.' },
          },
        },
      },
    ]
  : [];

const localTools = enableTools ? { bash: runBashTool } : {};

const agent = new CodexAgent({
  token,
  accountId,
  model,
  instructions,
  tools: toolSpecs,
  localTools,
  debugLog: () => {},
  useOpenAIWebSearch: enableTools,
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
