import sys
import time
import colorsys
import logging
import threading
from collections import deque
from datetime import datetime

try:
    import termios
except ImportError:  # pragma: no cover - non-POSIX
    termios = None

from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from pynput import mouse


class BufferLogHandler(logging.Handler):
    def __init__(self, buffer, buffer_lock):
        super().__init__()
        self.buffer = buffer
        self.buffer_lock = buffer_lock

    def emit(self, record):
        log_entry = self.format(record)
        with self.buffer_lock:
            ts = datetime.now().strftime("%m/%d %H:%M:%S")
            prefix = f"[yellow][{ts}][/yellow] "
            # Add color to log levels (gray override for background noise)
            if getattr(record, "gray", False):
                log_entry = f"[bright_black]{log_entry}[/bright_black]"
            elif record.levelno == logging.INFO:
                log_entry = f"[green]{log_entry}[/green]"
            elif record.levelno == logging.WARNING:
                log_entry = f"[yellow]{log_entry}[/yellow]"
            elif record.levelno == logging.ERROR:
                log_entry = f"[red]{log_entry}[/red]"
            elif record.levelno == logging.DEBUG:
                log_entry = f"[blue]{log_entry}[/blue]"
            self.buffer.append(prefix + log_entry)


class DisplayManager:
    """Render the Rich dashboard in its own loop."""

    def __init__(
        self,
        console: Console,
        profile_nickname,
        broadcaster,
        get_git_info,
        get_runtime_duration,
        get_attendance_count,
        log_window=7,
    ):
        self.console = console
        self.profile_nickname = profile_nickname
        self.broadcaster = broadcaster
        self.get_git_info = get_git_info
        self.get_runtime_duration = get_runtime_duration
        self.get_attendance_count = get_attendance_count
        self.log_window = log_window
        self.log_buffer = deque(maxlen=200)
        self.log_buffer_lock = threading.Lock()
        self.log_scroll_offset = 0
        self.log_scroll_lock = threading.Lock()
        self.refresh_event = threading.Event()
        self._buffer_handler = BufferLogHandler(self.log_buffer, self.log_buffer_lock)
        self._stdin_fd = None
        self._old_term_attrs = None

    def get_log_handler(self):
        return self._buffer_handler

    def adjust_log_scroll(self, delta):
        with self.log_buffer_lock, self.log_scroll_lock:
            max_offset = max(len(self.log_buffer) - self.log_window, 0)
            self.log_scroll_offset = min(max(self.log_scroll_offset + delta, 0), max_offset)
        self.refresh_event.set()

    def get_log_state(self):
        with self.log_buffer_lock, self.log_scroll_lock:
            n = len(self.log_buffer)
            offset = min(self.log_scroll_offset, max(n - self.log_window, 0))
            if n <= self.log_window:
                lines = list(self.log_buffer)
            else:
                bottom = max(self.log_window, min(n, n - offset))
                start = bottom - self.log_window
                end = bottom
                lines = list(self.log_buffer)[start:end]
            return {
                "lines": lines,
                "total": n,
                "offset": offset,
                "window": self.log_window,
            }

    def listen_for_scroll(self, exit_event):
        def on_scroll(x, y, dx, dy):
            try:
                if dy > 0:
                    self.adjust_log_scroll(1)
                elif dy < 0:
                    self.adjust_log_scroll(-1)
            except Exception:
                pass

        listener = mouse.Listener(on_scroll=on_scroll, suppress=False)
        listener.start()
        while not exit_event.is_set():
            time.sleep(0.2)
        listener.stop()

    def _nickname_color(self, t=None, speed=0.05):
        """Return a smoothly changing hex color for the profile label."""
        if t is None:
            t = time.time()
        hue = (t * speed) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def _enter_noecho(self):
        if termios is None:
            return
        if not sys.stdin or not sys.stdin.isatty():
            return
        try:
            fd = sys.stdin.fileno()
            attrs = termios.tcgetattr(fd)
            new_attrs = termios.tcgetattr(fd)
            new_attrs[3] = new_attrs[3] & ~termios.ECHO
            termios.tcsetattr(fd, termios.TCSADRAIN, new_attrs)
            self._stdin_fd = fd
            self._old_term_attrs = attrs
        except Exception:
            self._stdin_fd = None
            self._old_term_attrs = None

    def _restore_noecho(self):
        if termios is None:
            return
        if self._stdin_fd is None or self._old_term_attrs is None:
            return
        try:
            termios.tcsetattr(self._stdin_fd, termios.TCSADRAIN, self._old_term_attrs)
        except Exception:
            pass
        self._stdin_fd = None
        self._old_term_attrs = None

    def run(self, exit_event):
        git_commit, git_date, git_count = self.get_git_info()
        git_from_repo = True
        if git_commit == "unknown" or git_date == "unknown" or git_date == "release":
            git_from_repo = False
        try:
            git_count_display = str(int(git_count) - 1)
        except Exception:
            git_count_display = git_count

        self._enter_noecho()
        try:
            with Live(refresh_per_second=60, console=self.console, screen=True) as live:
                while not exit_event.is_set():
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    runtime = self.get_runtime_duration()
                    attendance = self.get_attendance_count()
                    log_state = self.get_log_state()
                    latest_logs = log_state.get("lines", [])
                    total_logs = log_state.get("total", 0)
                    offset = log_state.get("offset", 0)
                    window = log_state.get("window", 7)

                    broadcast_enabled = False
                    try:
                        broadcast_enabled = bool(getattr(self.broadcaster, "enabled", False))
                    except Exception:
                        broadcast_enabled = False

                    info_table = Table.grid(expand=True)
                    info_table.add_row(
                        f"[bold cyan]Current Time:[/bold cyan] {current_time}",
                        f"[bold green]Runtime Duration:[/bold green] {runtime}",
                        f"[bold yellow]Attendance Success Count:[/bold yellow] {attendance}",
                        f"[bold magenta]PandaQuQ:[/bold magenta] [link=https://github.com/PandaQuQ/RHUL_attendance_bot]GitHub Repo[/link]",
                    )

                    log_content = "\n".join(latest_logs) if latest_logs else "No logs available."

                    logs_table = Table.grid(expand=True)
                    if total_logs <= window:
                        logs_table.add_column(ratio=1)
                        logs_table.add_row(
                            Panel(
                                log_content,
                                title="[bold green]Latest Logs[/bold green]",
                                border_style="green",
                                padding=(1, 2),
                            )
                        )
                    else:
                        scrollbar_lines = []
                        thumb_size = max(1, int(window * window / total_logs))
                        track_size = window
                        max_thumb_pos = max(track_size - thumb_size, 0)
                        thumb_pos = max_thumb_pos - int((offset / max(total_logs - window, 1)) * max_thumb_pos)
                        for i in range(track_size):
                            if thumb_pos <= i < thumb_pos + thumb_size:
                                scrollbar_lines.append("█")
                            else:
                                scrollbar_lines.append("│")

                        scrollbar_text = Text("\n".join(scrollbar_lines))

                        logs_table.add_column(ratio=30)
                        logs_table.add_column(ratio=1, width=1)
                        logs_table.add_row(
                            Panel(
                                log_content,
                                title="[bold green]Latest Logs[/bold green]",
                                border_style="green",
                                padding=(1, 2),
                            ),
                            Panel(scrollbar_text, border_style="green", padding=(1, 0)),
                        )

                    instructions = Text.from_markup(
                        "Press [yellow][[/yellow] then [yellow]][/yellow] to manually trigger the next event\n"
                        "Press [yellow][[/yellow] then [yellow]c[/yellow] to refresh the calendar\n"
                        "Press [yellow][[/yellow] then [yellow]q[/yellow] to exit the script",
                        justify="center",
                    )
                    shortcut_instructions = Align.center(instructions, vertical="middle")

                    if git_from_repo:
                        version_number_text = Align.center(
                            f"This is the No.[red]{git_count_display}[/red] version", vertical="middle"
                        )
                    else:
                        version_number_text = Align.center(
                            f"Version: {git_count}", vertical="middle"
                        )
                    nick_color = self._nickname_color()
                    nickname_text = Align.center(
                        f"[bold]{'[white]Profile:[/]'} [{nick_color}]{self.profile_nickname}[/]", vertical="middle"
                    )
                    broadcast_status = (
                        "[green]Enabled[/green]" if broadcast_enabled else "[red]Disabled[/red]"
                    )
                    broadcast_text = Align.center(
                        f"Discord Broadcast: {broadcast_status}", vertical="middle"
                    )
                    if git_from_repo:
                        version_text = Align.center(
                            f"[bright_black]Commit: {git_commit} ({git_date})[/bright_black]",
                            vertical="middle",
                        )
                    else:
                        version_text = None

                    layout = Table.grid(expand=True)
                    layout.add_row(info_table)
                    layout.add_row(logs_table)
                    layout.add_row(nickname_text)
                    layout.add_row(broadcast_text)
                    layout.add_row(shortcut_instructions)
                    if version_text is not None:
                        layout.add_row(version_text)
                    layout.add_row(version_number_text)

                    live.update(layout)

                    if exit_event.wait(timeout=0):
                        break
                    # Wake early on scroll; otherwise short sleep to keep CPU low
                    if self.refresh_event.wait(timeout=0.02):
                        self.refresh_event.clear()
                        continue
                    time.sleep(0.02)
        finally:
            self._restore_noecho()
