"""journald log collection and parsing for Firedancer Health Exporter."""

import re
import subprocess
from datetime import datetime, timedelta, timezone

LOG_WINDOW_HOURS = 24
JOURNALD_UNIT = "firedancer"

RE_TOO_FEW = re.compile(r"TooFewTicks", re.IGNORECASE)
RE_METRICS = re.compile(r"metrics\s+submit\s+error", re.IGNORECASE)
RE_SEVERITY = re.compile(r"\b(ERROR|PANIC|FATAL)\b")


def fetch_logs() -> list[str]:
    since = (
        datetime.now(timezone.utc) - timedelta(hours=LOG_WINDOW_HOURS)
    ).strftime("%Y-%m-%d %H:%M:%S")
    result = subprocess.run(
        ["journalctl", "-u", JOURNALD_UNIT, "--since", since, "--no-pager", "-o", "short-iso"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"journalctl exited {result.returncode}: {result.stderr.strip()}")
    lines = result.stdout.splitlines()
    return [] if (len(lines) == 1 and "No entries" in lines[0]) else lines


def parse_logs(lines: list[str]) -> dict:
    """Parse log lines and return counts of notable events.

    Returns a dict with keys: total, too_few_ticks, metrics_errors, critical.
    A line containing TooFewTicks is never counted as a critical (ERROR/PANIC/FATAL) event.
    """
    too_few_ticks = metrics_errors = critical_count = 0
    for line in lines:
        is_too_few = bool(RE_TOO_FEW.search(line))
        if is_too_few:
            too_few_ticks += 1
        if RE_METRICS.search(line):
            metrics_errors += 1
        if RE_SEVERITY.search(line) and not is_too_few:
            critical_count += 1
    return {
        "total": len(lines),
        "too_few_ticks": too_few_ticks,
        "metrics_errors": metrics_errors,
        "critical": critical_count,
    }
