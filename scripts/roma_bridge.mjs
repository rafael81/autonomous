import crypto from 'node:crypto';
import process from 'node:process';
import fs from 'node:fs';
import path from 'node:path';
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

function resolveToolPath(candidate = '.') {
  const raw = typeof candidate === 'string' && candidate.trim() ? candidate.trim() : '.';
  return path.isAbsolute(raw) ? raw : path.resolve(toolCwd, raw);
}

async function listDirTool(args = {}) {
  const dir = resolveToolPath(args.path || '.');
  const maxEntries = Number.isFinite(args.max_entries) ? Math.max(1, Math.min(200, Number(args.max_entries))) : 50;
  const entries = fs.readdirSync(dir, { withFileTypes: true }).slice(0, maxEntries);
  return entries
    .map((entry) => `${entry.isDirectory() ? 'dir' : 'file'}\t${entry.name}`)
    .join('\n');
}

async function searchFilesTool(args = {}) {
  const query = typeof args.query === 'string' ? args.query.trim() : '';
  if (!query) {
    return 'Error: query is required.';
  }
  const dir = resolveToolPath(args.path || '.');
  const maxResults = Number.isFinite(args.max_results) ? Math.max(1, Math.min(200, Number(args.max_results))) : 50;
  const results = [];
  const visit = (current) => {
    if (results.length >= maxResults) return;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      if (entry.name === '.git' || entry.name === 'node_modules' || entry.name === '.venv') continue;
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        visit(fullPath);
        if (results.length >= maxResults) return;
        continue;
      }
      if (entry.name.toLowerCase().includes(query.toLowerCase())) {
        results.push(path.relative(toolCwd, fullPath));
        if (results.length >= maxResults) return;
      }
    }
  };
  visit(dir);
  return results.length > 0 ? results.join('\n') : '(no matches)';
}

async function readFileTool(args = {}) {
  const filePath = resolveToolPath(args.path);
  const startLine = Number.isFinite(args.start_line) ? Math.max(1, Number(args.start_line)) : 1;
  const endLine = Number.isFinite(args.end_line) ? Math.max(startLine, Number(args.end_line)) : startLine + 199;
  const lines = fs.readFileSync(filePath, 'utf-8').split('\n');
  return lines
    .slice(startLine - 1, endLine)
    .map((line, index) => `${startLine + index}: ${line}`)
    .join('\n');
}

async function grepTextTool(args = {}) {
  const pattern = typeof args.pattern === 'string' ? args.pattern.trim() : '';
  if (!pattern) {
    return 'Error: pattern is required.';
  }
  const dir = resolveToolPath(args.path || '.');
  const maxResults = Number.isFinite(args.max_results) ? Math.max(1, Math.min(200, Number(args.max_results))) : 50;
  const caseSensitive = args.case_sensitive === true;
  const results = [];
  const matcher = caseSensitive
    ? (text) => text.includes(pattern)
    : (text) => text.toLowerCase().includes(pattern.toLowerCase());
  const visit = (current) => {
    if (results.length >= maxResults) return;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      if (entry.name === '.git' || entry.name === 'node_modules' || entry.name === '.venv') continue;
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        visit(fullPath);
        if (results.length >= maxResults) return;
        continue;
      }
      let lines;
      try {
        lines = fs.readFileSync(fullPath, 'utf-8').split('\n');
      } catch {
        continue;
      }
      for (let index = 0; index < lines.length; index += 1) {
        if (matcher(lines[index])) {
          results.push(`${path.relative(toolCwd, fullPath)}:${index + 1}: ${lines[index]}`);
          if (results.length >= maxResults) return;
        }
      }
    }
  };
  visit(dir);
  return results.length > 0 ? results.join('\n') : '(no matches)';
}

const toolSpecs = enableTools
  ? [
      {
        type: 'function',
        name: 'list_dir',
        description: 'List files and directories in a workspace path.',
        parameters: {
          type: 'object',
          properties: {
            path: { type: 'string', description: 'Directory path relative to the workspace.' },
            max_entries: { type: 'number', description: 'Maximum entries to return.' },
          },
        },
      },
      {
        type: 'function',
        name: 'search_files',
        description: 'Search for files whose names match a query string.',
        parameters: {
          type: 'object',
          required: ['query'],
          properties: {
            query: { type: 'string', description: 'Case-insensitive file name fragment.' },
            path: { type: 'string', description: 'Search root relative to the workspace.' },
            max_results: { type: 'number', description: 'Maximum number of matches to return.' },
          },
        },
      },
      {
        type: 'function',
        name: 'read_file',
        description: 'Read a file or a bounded line range from the workspace.',
        parameters: {
          type: 'object',
          required: ['path'],
          properties: {
            path: { type: 'string', description: 'File path relative to the workspace.' },
            start_line: { type: 'number', description: '1-based start line.' },
            end_line: { type: 'number', description: '1-based end line.' },
          },
        },
      },
      {
        type: 'function',
        name: 'grep_text',
        description: 'Search file contents in the workspace for a text pattern.',
        parameters: {
          type: 'object',
          required: ['pattern'],
          properties: {
            pattern: { type: 'string', description: 'Text pattern to search for.' },
            path: { type: 'string', description: 'Search root relative to the workspace.' },
            max_results: { type: 'number', description: 'Maximum matching lines to return.' },
            case_sensitive: { type: 'boolean', description: 'Whether matching is case-sensitive.' },
          },
        },
      },
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

const localTools = enableTools
  ? {
      list_dir: listDirTool,
      search_files: searchFilesTool,
      read_file: readFileTool,
      grep_text: grepTextTool,
      bash: runBashTool,
    }
  : {};

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
