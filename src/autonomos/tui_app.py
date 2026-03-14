"""Textual TUI for Autonomos."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, UTC

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual import events
from textual.events import Focus, Key
from textual.widgets import Button, Footer, Header, Input, Static

from .app import run_chat
from .memory import list_sessions
from .orchestration import write_approval_response, write_request_user_input_response
from .tui_state import TuiSessionState


@dataclass(frozen=True)
class TuiConfig:
    profile: str
    cwd: Path
    captures_dir: Path
    promote_dir: Path
    baselines_dir: Path
    memory_dir: Path
    session_id: str
    debug_log_path: Path | None = None


class AutonomosTui(App[None]):
    AUTO_FOCUS = "#composer"

    CSS = """
    Screen {
        layout: vertical;
    }
    #body {
        height: 1fr;
    }
    #left-pane {
        width: 3fr;
        height: 1fr;
    }
    #right-pane {
        width: 2fr;
        height: 1fr;
    }
    .panel {
        border: solid $panel;
        padding: 0 1;
    }
    #transcript {
        height: 1fr;
        min-height: 8;
    }
    #sidebar {
        height: 1fr;
    }
    #parity, #diagnostics, #sessions {
        height: 1fr;
        min-height: 3;
    }
    #composer {
        height: auto;
        min-height: 3;
    }
    #controls {
        height: auto;
    }
    #composer-hint {
        color: $text-muted;
        height: auto;
    }
    """

    BINDINGS = [
        ("ctrl+l", "clear_composer", "Clear"),
        ("ctrl+r", "refresh_sessions", "Sessions"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, config: TuiConfig) -> None:
        super().__init__()
        self.config = config
        self.state = TuiSessionState(session_id=config.session_id, memory_dir=config.memory_dir)
        self._busy = False
        self._debug_log_path = config.debug_log_path or (config.memory_dir.parent / "tui-debug.log")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._status_text(), id="statusbar", classes="panel")
        with Horizontal(id="body"):
            with Vertical(id="left-pane"):
                yield Static("", id="transcript", classes="panel")
            with Vertical(id="right-pane", classes="panel"):
                yield Static("", id="parity")
                yield Static("", id="diagnostics")
                yield Static("", id="sessions")
        with Container(id="controls", classes="panel"):
            yield Static("Type a prompt and press Enter. Use /sessions, /context, /session <id>, /approve, /decline, /choose.", id="composer-hint")
            yield Input(placeholder="Ask Autonomos...", id="composer")
            with Horizontal():
                yield Button("Approve", id="approve")
                yield Button("Decline", id="decline")
                yield Button("Use Recommended", id="choose")
                yield Button("Refresh Sessions", id="refresh")
        yield Footer()

    def on_mount(self) -> None:
        self._debug("mount")
        self._refresh_sidebar()
        self._append_transcript(f"status> session {self.config.session_id} ready")
        self.call_after_refresh(self._focus_composer)
        self.set_timer(0.05, self._focus_composer)
        self.set_timer(0.2, self._focus_composer)

    def on_ready(self, event: events.Ready) -> None:
        event.stop()
        self._debug(f"ready app_focus={self.app_focus}")
        for button in self.query(Button):
            button.can_focus = False
        self._focus_composer()
        self.set_timer(0.05, self._focus_composer)

    def on_focus(self, event: Focus) -> None:
        widget = getattr(event, "control", None) or event.screen.focused
        widget_id = getattr(widget, "id", None)
        self._debug(f"focus widget={type(widget).__name__ if widget else 'None'} id={widget_id}")

    def on_key(self, event: Key) -> None:
        if event.is_printable and event.character:
            composer = self._get_composer()
            if composer is None:
                return
            composer.value += event.character
            self._debug(f"app_key printable value={composer.value!r}")
            event.prevent_default()
            event.stop()
            return
        if event.key == "backspace":
            composer = self._get_composer()
            if composer is None:
                return
            composer.value = composer.value[:-1]
            self._debug(f"app_key backspace value={composer.value!r}")
            event.prevent_default()
            event.stop()
            return
        if event.key == "enter":
            composer = self._get_composer()
            if composer is None:
                return
            self._debug(f"app_key enter value={composer.value!r}")
            event.prevent_default()
            event.stop()
            self._submit_from_composer()
            return

    def action_submit(self) -> None:
        self._submit_from_composer()

    def action_clear_composer(self) -> None:
        self.query_one("#composer", Input).value = ""
        self._focus_composer()

    def action_refresh_sessions(self) -> None:
        self._refresh_sessions()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            self._refresh_sessions()
        elif event.button.id == "approve":
            self._handle_approval("Approve")
        elif event.button.id == "decline":
            self._handle_approval("Decline")
        elif event.button.id == "choose":
            self._handle_user_input_choice()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "composer":
            return
        self._debug(f"input_submitted value={event.value!r}")
        self._submit_from_composer()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "composer":
            return
        self._debug(f"input_changed value={event.value!r}")

    def _focus_composer(self) -> None:
        composer = self._get_composer()
        if composer is None:
            return
        self.set_focus(composer)
        self._debug("focus_composer")

    def _get_composer(self) -> Input | None:
        try:
            return self.query_one("#composer", Input)
        except NoMatches:
            return None

    def _submit_from_composer(self) -> None:
        if self._busy:
            self._debug("submit blocked busy")
            self._append_transcript("status> already running")
            return
        composer = self.query_one("#composer", Input)
        prompt = composer.value.strip()
        self._debug(f"submit prompt={prompt!r}")
        if not prompt:
            self._focus_composer()
            return
        composer.value = ""
        if self._handle_builtin_command(prompt):
            self._focus_composer()
            return
        self.state.add_user_prompt(prompt)
        self._append_transcript(f"user> {prompt}")
        asyncio.create_task(self._run_prompt(prompt))

    def _handle_builtin_command(self, prompt: str) -> bool:
        if prompt in {"/exit", "/quit"}:
            self.exit()
            return True
        if prompt == "/sessions":
            self._refresh_sessions()
            self._append_transcript("status> refreshed session list")
            return True
        if prompt == "/context":
            self._append_transcript(self.state.context_text().strip())
            return True
        if prompt == "/clear":
            self.state.transcript_lines.clear()
            self._replace_transcript(self.state.transcript_lines)
            return True
        if prompt == "/new":
            self.state.session_id = f"session-{asyncio.get_event_loop().time():.0f}"
            self._append_transcript(f"status> switched to {self.state.session_id}")
            self._refresh_sidebar()
            return True
        if prompt.startswith("/session "):
            _, _, session_id = prompt.partition(" ")
            self.state.session_id = session_id.strip() or self.state.session_id
            self._append_transcript(f"status> switched to {self.state.session_id}")
            self._refresh_sidebar()
            return True
        if prompt.startswith("/approve"):
            notes = prompt.removeprefix("/approve").strip()
            self._handle_approval("Approve", notes=notes)
            return True
        if prompt.startswith("/decline"):
            notes = prompt.removeprefix("/decline").strip()
            self._handle_approval("Decline", notes=notes)
            return True
        if prompt.startswith("/choose"):
            notes = prompt.removeprefix("/choose").strip()
            self._handle_user_input_choice(notes=notes)
            return True
        return False

    async def _run_prompt(
        self,
        prompt: str,
        *,
        request_user_input_response_path: Path | None = None,
        approval_response_path: Path | None = None,
    ) -> None:
        self._busy = True
        self._debug(f"run_prompt start prompt={prompt!r}")
        self._set_status(f"running {self.state.session_id}")
        self._append_transcript("status> Roma is thinking...")
        prior_len = len(self.state.transcript_lines)
        summary = await asyncio.to_thread(
            run_chat,
            prompt=prompt,
            profile=self.config.profile,
            cwd=self.config.cwd,
            captures_dir=self.config.captures_dir,
            promote_dir=self.config.promote_dir,
            baselines_dir=self.config.baselines_dir,
            memory_dir=self.config.memory_dir,
            session_id=self.state.session_id,
            request_user_input_response_path=request_user_input_response_path,
            approval_response_path=approval_response_path,
        )
        self.state.apply_summary(summary)
        self._debug(
            "run_prompt done "
            f"final={summary.final_message!r} "
            f"strategy={summary.strategy_id!r} "
            f"normalized={summary.normalized_path!s}"
        )
        await self._render_new_transcript_lines(prior_len)
        self._refresh_sidebar()
        self._busy = False
        self._set_status(f"idle {self.state.session_id}")
        self._focus_composer()

    def _handle_approval(self, decision: str, *, notes: str = "") -> None:
        if self._busy:
            return
        pending = self.state.pending_approval
        if pending is None:
            self._append_transcript("status> no pending approval")
            return
        response_path = write_approval_response(
            request_path=pending.request_path,
            decision=decision,
            notes=notes,
        )
        self._append_transcript(f"status> approval response saved to {response_path}")
        self.state.pending_approval = None
        asyncio.create_task(self._run_prompt("continue", approval_response_path=response_path))

    def _handle_user_input_choice(self, *, notes: str = "") -> None:
        if self._busy:
            return
        pending = self.state.pending_user_input
        if pending is None:
            self._append_transcript("status> no pending request-user-input")
            return
        selected = pending.options[0]["label"] if pending.options else "default"
        response_path = write_request_user_input_response(
            request_path=pending.request_path,
            selected_option=selected,
            notes=notes,
        )
        self._append_transcript(f"status> request-user-input response saved to {response_path}")
        self.state.pending_user_input = None
        asyncio.create_task(self._run_prompt("continue", request_user_input_response_path=response_path))

    def _refresh_sidebar(self) -> None:
        self.query_one("#parity", Static).update("\n".join(self.state.parity_lines or ["No parity data yet."]))
        self.query_one("#diagnostics", Static).update("\n".join(self._diagnostic_block()))
        self.query_one("#sessions", Static).update("\n".join(self._session_block()))
        self._set_status(self._status_text())

    def _refresh_sessions(self) -> None:
        self.query_one("#sessions", Static).update("\n".join(self._session_block()))

    def _diagnostic_block(self) -> list[str]:
        lines = [f"session: {self.state.session_id}"]
        if self.state.pending_approval:
            lines.append(f"approval: {self.state.pending_approval.question}")
        if self.state.pending_user_input:
            lines.append(f"request-user-input: {self.state.pending_user_input.question}")
        lines.extend(self.state.diagnostics_lines or ["No diagnostics yet."])
        return lines

    def _session_block(self) -> list[str]:
        rows = list_sessions(self.config.memory_dir)
        if not rows:
            return ["No saved sessions."]
        lines = ["Sessions:"]
        for session_id, count, last_ts in rows[:8]:
            marker = "*" if session_id == self.state.session_id else "-"
            lines.append(f"{marker} {session_id} ({count}) {last_ts or '-'}")
        return lines

    def _replace_transcript(self, lines: list[str]) -> None:
        self.query_one("#transcript", Static).update("\n".join(lines))
        self._debug(f"replace_transcript count={len(lines)}")

    async def _render_new_transcript_lines(self, prior_len: int) -> None:
        new_lines = self.state.transcript_lines[prior_len:]
        if not new_lines:
            return
        if prior_len == 0:
            self._replace_transcript(self.state.transcript_lines)
            return
        if len(new_lines) > 14:
            batch_size = 4
            for index in range(0, len(new_lines), batch_size):
                self._replace_transcript(self.state.transcript_lines[: prior_len + index + batch_size])
                await asyncio.sleep(0.02)
            return
        for offset, _line in enumerate(new_lines, start=1):
            self._replace_transcript(self.state.transcript_lines[: prior_len + offset])
            await asyncio.sleep(0.03)

    def _append_transcript(self, line: str) -> None:
        self.state.transcript_lines.append(line)
        self._replace_transcript(self.state.transcript_lines)
        self._debug(f"append_transcript line={line!r}")

    def _set_status(self, text: str) -> None:
        self.query_one("#statusbar", Static).update(text)

    def _status_text(self) -> str:
        state = "busy" if self._busy else "idle"
        return f"Autonomos TUI | {state} | session={self.state.session_id}"

    def _debug(self, message: str) -> None:
        self._debug_log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).isoformat()
        with self._debug_log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {self.config.session_id} {message}\n")


def run_tui(config: TuiConfig) -> None:
    app = AutonomosTui(config)
    app.run()
