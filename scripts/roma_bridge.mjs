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
const policy = payload.policy && typeof payload.policy === 'object' ? payload.policy : {};
const excludedRoots = new Set(Array.isArray(policy.excludedRoots) ? policy.excludedRoots : ['.git', '.venv', 'node_modules']);
const preferredRoots = Array.isArray(policy.preferredRoots) ? policy.preferredRoots : [];
const toolBudget = Number.isFinite(policy.toolBudget) ? Math.max(1, Number(policy.toolBudget)) : 6;
const maxRepeatedToolCalls = Number.isFinite(policy.maxRepeatedToolCalls)
  ? Math.max(1, Number(policy.maxRepeatedToolCalls))
  : 2;
const stopAfterEvidence = Number.isFinite(policy.stopAfterEvidence) ? Math.max(1, Number(policy.stopAfterEvidence)) : 2;
const promptMode = typeof policy.promptMode === 'string' ? policy.promptMode : 'general';
const inspectionMode = promptMode === 'repository_inspection' || promptMode === 'inspection_and_verification';
const toolUsage = new Map();
let evidenceCount = 0;

const emit = (event) => {
  process.stdout.write(`${JSON.stringify(event)}\n`);
};

const nowMs = () => Date.now();

function relativeFromWorkspace(targetPath) {
  return path.relative(toolCwd, targetPath).replace(/\\/g, '/') || '.';
}

function isExcludedName(name) {
  return excludedRoots.has(name);
}

function isExcludedPath(targetPath) {
  const relative = relativeFromWorkspace(targetPath);
  return relative.split('/').some((part) => excludedRoots.has(part));
}

function noteToolUsage(toolName, summary = {}) {
  const count = (toolUsage.get(toolName) || 0) + 1;
  toolUsage.set(toolName, count);
  emit({ type: 'tool_profile', name: toolName, count, summary });
}

function toolBudgetExceeded(toolName) {
  const total = Array.from(toolUsage.values()).reduce((sum, count) => sum + count, 0);
  const repeated = toolUsage.get(toolName) || 0;
  return total >= toolBudget || repeated >= maxRepeatedToolCalls;
}

function shouldDeclineTool(toolName) {
  if (toolBudgetExceeded(toolName)) {
    return `Error: tool budget exceeded for ${toolName}.`;
  }
  if (inspectionMode && evidenceCount >= stopAfterEvidence && toolName !== 'read_file') {
    return `Error: enough evidence gathered; skip ${toolName}.`;
  }
  if (inspectionMode && toolName === 'bash') {
    return 'Error: bash is disabled for repository inspection; use built-in inspection tools.';
  }
  return null;
}

const { token, accountId } = getCodexCredentials();
if (!token || !accountId) {
  emit({ type: 'error', message: 'Codex credentials not found in ~/.codex/auth.json' });
  process.exit(2);
}

const sessionId = crypto.randomUUID();
emit({ type: 'session_start', session_id: sessionId, model });

async function runBashTool(args = {}) {
  const decline = shouldDeclineTool('bash');
  if (decline) {
    return decline;
  }
  const command = typeof args.command === 'string' ? args.command.trim() : '';
  if (!command) {
    return 'Error: command is required.';
  }

  const cwd = typeof args.cwd === 'string' && args.cwd.trim() ? args.cwd.trim() : toolCwd;
  const timeoutMs = Number.isFinite(args.timeout_ms) ? Math.max(500, Math.min(30000, Number(args.timeout_ms))) : 8000;
  const shell = typeof args.shell === 'string' && args.shell.trim() ? args.shell.trim() : '/bin/bash';
  const maxOutputChars = Number.isFinite(args.max_output_chars) ? Math.max(256, Math.min(16000, Number(args.max_output_chars))) : 8000;
  const startedAt = nowMs();

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
      evidenceCount += stdout || stderr ? 1 : 0;
      noteToolUsage('bash', {
        command,
        duration_ms: nowMs() - startedAt,
        stdout_chars: stdout.length,
        stderr_chars: stderr.length,
        exit_code: code ?? 'n/a',
      });
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
  const decline = shouldDeclineTool('list_dir');
  if (decline) {
    return decline;
  }
  const dir = resolveToolPath(args.path || '.');
  if (isExcludedPath(dir)) {
    return `Error: excluded path ${relativeFromWorkspace(dir)}.`;
  }
  const requestedMaxEntries = Number.isFinite(args.max_entries) ? Number(args.max_entries) : 50;
  const maxEntries = Math.max(1, Math.min(40, requestedMaxEntries));
  const startedAt = nowMs();
  const entries = fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((entry) => !isExcludedName(entry.name))
    .filter(
      (entry) =>
        preferredRoots.length === 0 ||
        relativeFromWorkspace(dir) !== '.' ||
        preferredRoots.includes(entry.name) ||
        !entry.isDirectory()
    )
    .slice(0, maxEntries);
  evidenceCount += entries.length > 0 ? 1 : 0;
  noteToolUsage('list_dir', {
    path: relativeFromWorkspace(dir),
    entry_count: entries.length,
    duration_ms: nowMs() - startedAt,
  });
  return entries
    .map((entry) => `${entry.isDirectory() ? 'dir' : 'file'}\t${entry.name}`)
    .join('\n');
}

async function searchFilesTool(args = {}) {
  const decline = shouldDeclineTool('search_files');
  if (decline) {
    return decline;
  }
  const query = typeof args.query === 'string' ? args.query.trim() : '';
  if (!query) {
    return 'Error: query is required.';
  }
  const dir = resolveToolPath(args.path || '.');
  if (isExcludedPath(dir)) {
    return `Error: excluded path ${relativeFromWorkspace(dir)}.`;
  }
  const maxResults = Number.isFinite(args.max_results) ? Math.max(1, Math.min(200, Number(args.max_results))) : 50;
  const results = [];
  const startedAt = nowMs();
  const visit = (current) => {
    if (results.length >= maxResults) return;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      if (isExcludedName(entry.name)) continue;
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
  evidenceCount += results.length > 0 ? 1 : 0;
  noteToolUsage('search_files', {
    path: relativeFromWorkspace(dir),
    query,
    result_count: results.length,
    duration_ms: nowMs() - startedAt,
  });
  return results.length > 0 ? results.join('\n') : '(no matches)';
}

async function readFileTool(args = {}) {
  const decline = shouldDeclineTool('read_file');
  if (decline) {
    return decline;
  }
  const filePath = resolveToolPath(args.path);
  if (isExcludedPath(filePath)) {
    return `Error: excluded path ${relativeFromWorkspace(filePath)}.`;
  }
  const startedAt = nowMs();
  const startLine = Number.isFinite(args.start_line) ? Math.max(1, Number(args.start_line)) : 1;
  const maxSpan = 80;
  const requestedEndLine = Number.isFinite(args.end_line) ? Number(args.end_line) : startLine + 39;
  const endLine = Math.min(Math.max(startLine, requestedEndLine), startLine + maxSpan - 1);
  const lines = fs.readFileSync(filePath, 'utf-8').split('\n');
  evidenceCount += 1;
  noteToolUsage('read_file', {
    path: relativeFromWorkspace(filePath),
    start_line: startLine,
    end_line: endLine,
    duration_ms: nowMs() - startedAt,
  });
  return lines
    .slice(startLine - 1, endLine)
    .map((line, index) => `${startLine + index}: ${line}`)
    .join('\n');
}

async function grepTextTool(args = {}) {
  const decline = shouldDeclineTool('grep_text');
  if (decline) {
    return decline;
  }
  const pattern = typeof args.pattern === 'string' ? args.pattern.trim() : '';
  if (!pattern) {
    return 'Error: pattern is required.';
  }
  const dir = resolveToolPath(args.path || '.');
  if (isExcludedPath(dir)) {
    return `Error: excluded path ${relativeFromWorkspace(dir)}.`;
  }
  const maxResults = Number.isFinite(args.max_results) ? Math.max(1, Math.min(200, Number(args.max_results))) : 50;
  const caseSensitive = args.case_sensitive === true;
  const results = [];
  const startedAt = nowMs();
  const matcher = caseSensitive
    ? (text) => text.includes(pattern)
    : (text) => text.toLowerCase().includes(pattern.toLowerCase());
  const visit = (current) => {
    if (results.length >= maxResults) return;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      if (isExcludedName(entry.name)) continue;
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
  evidenceCount += results.length > 0 ? 1 : 0;
  noteToolUsage('grep_text', {
    path: relativeFromWorkspace(dir),
    pattern,
    result_count: results.length,
    duration_ms: nowMs() - startedAt,
  });
  return results.length > 0 ? results.join('\n') : '(no matches)';
}

async function globPathsTool(args = {}) {
  const decline = shouldDeclineTool('glob_paths');
  if (decline) {
    return decline;
  }
  const pattern = typeof args.pattern === 'string' ? args.pattern.trim() : '';
  if (!pattern) {
    return 'Error: pattern is required.';
  }
  const root = resolveToolPath(args.path || '.');
  if (isExcludedPath(root)) {
    return `Error: excluded path ${relativeFromWorkspace(root)}.`;
  }
  const maxResults = Number.isFinite(args.max_results) ? Math.max(1, Math.min(200, Number(args.max_results))) : 100;
  const relativePattern = path.isAbsolute(pattern) ? path.relative(root, pattern) : pattern;
  const normalizedPattern = relativePattern.replace(/\\/g, '/');
  const segments = normalizedPattern.split('/').filter(Boolean);
  const matches = [];

  const wildcardToRegExp = (segment) =>
    new RegExp(
      '^' + segment
        .replace(/[.+^${}()|[\]\\]/g, '\\$&')
        .replace(/\*/g, '.*')
        .replace(/\?/g, '.') + '$'
    );

  const startedAt = nowMs();
  const walk = (currentDir, index, relativeBase = '') => {
    if (matches.length >= maxResults) return;
    if (index >= segments.length) {
      if (relativeBase) matches.push(relativeBase);
      return;
    }
    const segment = segments[index];
    if (segment === '**') {
      walk(currentDir, index + 1, relativeBase);
      for (const entry of fs.readdirSync(currentDir, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        if (isExcludedName(entry.name)) continue;
        const nextBase = relativeBase ? `${relativeBase}/${entry.name}` : entry.name;
        walk(path.join(currentDir, entry.name), index, nextBase);
        if (matches.length >= maxResults) return;
      }
      return;
    }

    const matcher = wildcardToRegExp(segment);
    for (const entry of fs.readdirSync(currentDir, { withFileTypes: true })) {
      if (isExcludedName(entry.name)) continue;
      if (!matcher.test(entry.name)) continue;
      const nextBase = relativeBase ? `${relativeBase}/${entry.name}` : entry.name;
      const nextPath = path.join(currentDir, entry.name);
      if (index === segments.length - 1) {
        matches.push(nextBase);
      } else if (entry.isDirectory()) {
        walk(nextPath, index + 1, nextBase);
      }
      if (matches.length >= maxResults) return;
    }
  };

  walk(root, 0);
  evidenceCount += matches.length > 0 ? 1 : 0;
  noteToolUsage('glob_paths', {
    path: relativeFromWorkspace(root),
    pattern,
    result_count: matches.length,
    duration_ms: nowMs() - startedAt,
  });
  return matches.length > 0 ? matches.join('\n') : '(no matches)';
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
        name: 'glob_paths',
        description: 'Match workspace paths using glob patterns like *.py or src/**/test_*.py.',
        parameters: {
          type: 'object',
          required: ['pattern'],
          properties: {
            pattern: { type: 'string', description: 'Glob pattern relative to the workspace or provided path.' },
            path: { type: 'string', description: 'Root directory relative to the workspace.' },
            max_results: { type: 'number', description: 'Maximum matches to return.' },
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
      glob_paths: globPathsTool,
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
  emit({
    type: 'session_end',
    ok: true,
    tool_summary: Object.fromEntries(toolUsage),
    evidence_count: evidenceCount,
    tool_budget: toolBudget,
    stop_after_evidence: stopAfterEvidence,
  });
} catch (error) {
  emit({ type: 'error', message: error instanceof Error ? error.message : String(error) });
  emit({
    type: 'session_end',
    ok: false,
    tool_summary: Object.fromEntries(toolUsage),
    evidence_count: evidenceCount,
    tool_budget: toolBudget,
    stop_after_evidence: stopAfterEvidence,
  });
  process.exit(1);
}
