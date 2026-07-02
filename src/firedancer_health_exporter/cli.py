"""CLI diagnostic tool — one-shot colored report from journald logs."""

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import re
import subprocess

RE_TIMESTAMP = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}):\d{2}:\d{2}[+-]\d{4}")
RE_TOO_FEW = re.compile(r"TooFewTicks", re.IGNORECASE)
RE_METRICS = re.compile(r"metrics\s+submit\s+error", re.IGNORECASE)
RE_SEVERITY = re.compile(r"\b(ERROR|PANIC|FATAL)\b")


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    DIM = "\033[2m"


def _no_color() -> bool:
    return not sys.stdout.isatty() or os.environ.get("NO_COLOR") is not None


def _color(text: str, code: str) -> str:
    return text if _no_color() else f"{code}{text}{C.RESET}"


def fetch_logs() -> list[str]:
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    cmd = ["journalctl", "-u", "firedancer", "--since", since, "--no-pager", "-o", "short-iso"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        print(f"{C.RED}ERROR: journalctl not found — is this a systemd system?{C.RESET}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"{C.RED}ERROR: journalctl timed out{C.RESET}")
        sys.exit(1)

    if result.returncode not in (0, 1):
        print(f"{C.RED}journalctl error:{C.RESET} {result.stderr.strip()}")
        sys.exit(result.returncode)

    lines = result.stdout.splitlines()
    return [] if not lines or (len(lines) == 1 and "No entries" in lines[0]) else lines


def parse_logs(lines: list[str]) -> dict:
    too_few_ticks = 0
    metrics_errors = 0
    critical: list[str] = []
    by_hour: dict[str, int] = defaultdict(int)

    for line in lines:
        hour_match = RE_TIMESTAMP.match(line)
        hour_key = hour_match.group(1) if hour_match else "unknown"

        if RE_TOO_FEW.search(line):
            too_few_ticks += 1
            by_hour[hour_key] += 1

        if RE_METRICS.search(line):
            metrics_errors += 1

        if RE_SEVERITY.search(line) and not RE_TOO_FEW.search(line):
            critical.append(line)

    return {
        "total": len(lines),
        "too_few_ticks": too_few_ticks,
        "metrics_errors": metrics_errors,
        "critical": critical,
        "by_hour": dict(sorted(by_hour.items())),
    }


def render_histogram(by_hour: dict[str, int], width: int = 40) -> str:
    if not by_hour:
        return "  (no TooFewTicks events)\n"
    max_val = max(by_hour.values())
    rows = []
    for hour, count in sorted(by_hour.items()):
        bar = "█" * (int(count / max_val * width) if max_val else 0)
        rows.append(f"  {hour}  {bar} {count}")
    return "\n".join(rows)


def print_report(data: dict) -> None:
    sep = _color("=" * 60, C.DIM)
    print()
    print(sep)
    print(_color("  FIREDANCER LOG ANALYSIS — LAST 24 HOURS", C.BOLD + C.CYAN))
    print(sep)
    print(f"\n  {_color('Total log lines:', C.BOLD)} {data['total']}")

    tft = data["too_few_ticks"]
    print(
        f"\n  {_color('TooFewTicks warnings:', C.BOLD)} "
        f"{_color(str(tft), C.YELLOW if tft > 0 else C.GREEN)}"
    )

    me = data["metrics_errors"]
    print(
        f"  {_color('Metrics submit errors:', C.BOLD)} "
        f"{_color(str(me), C.YELLOW if me > 0 else C.GREEN)}"
    )

    crit = data["critical"]
    print(
        f"  {_color('ERROR/PANIC/FATAL events:', C.BOLD)} "
        f"{_color(str(len(crit)), C.RED if crit else C.GREEN)}"
    )

    print(f"\n{_color('  TooFewTicks by hour:', C.BOLD + C.MAGENTA)}")
    print(render_histogram(data["by_hour"]))

    if crit:
        print(f"\n{_color('  Critical log lines:', C.BOLD + C.RED)}")
        for line in crit[:50]:
            print(f"  {_color(line, C.RED)}")
        if len(crit) > 50:
            print(f"  {_color(f'... and {len(crit) - 50} more', C.DIM)}")

    print()
    print(sep)
    if not crit and tft == 0 and me == 0:
        verdict = _color("  ✓ No issues detected — node looks healthy", C.GREEN + C.BOLD)
    elif crit:
        verdict = _color("  ✗ Critical errors found — investigate immediately", C.RED + C.BOLD)
    else:
        verdict = _color("  ⚠ Warnings present — monitor the node", C.YELLOW + C.BOLD)
    print(verdict)
    print(sep)
    print()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="firedancer-analyze",
        description="Firedancer node diagnostic tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--full",
        action="store_true",
        help="Show detailed report with explanations, recommendations, and status indicators",
    )
    p.add_argument(
        "--lang",
        choices=["en", "ru"],
        default="en",
        metavar="LANG",
        help="Report language: en or ru (default: en)",
    )
    rpc = p.add_argument_group("RPC metrics (used with --full)")
    rpc.add_argument(
        "--rpc-url",
        default="http://127.0.0.1:8899",
        help="Solana RPC endpoint URL",
    )
    rpc.add_argument(
        "--vote-account",
        default="",
        metavar="PUBKEY",
        help="Validator vote account public key",
    )
    rpc.add_argument(
        "--identity",
        default="",
        metavar="PUBKEY",
        help="Validator identity public key",
    )
    rpc.add_argument(
        "--withdrawer",
        default="",
        metavar="PUBKEY",
        help="Withdrawer account public key (optional)",
    )
    return p


def _run_full_report(args: argparse.Namespace) -> None:
    from .reporter import render_full_report
    from .rpc_client import (
        compute_vote_credits_metrics,
        get_balance,
        get_block_production,
        get_epoch_data,
        get_validator_data,
    )

    lang = args.lang

    print(_color("Fetching Firedancer logs (last 24 h)…", C.DIM))
    lines = fetch_logs()
    if lines:
        log_data = parse_logs(lines)
    else:
        log_data = {"total": 0, "too_few_ticks": 0, "metrics_errors": 0, "critical": [], "by_hour": {}}

    rpc_data = None
    if args.vote_account or args.identity:
        try:
            rpc_data = get_validator_data(args.rpc_url, args.vote_account, args.identity)
        except Exception as exc:
            print(_color(f"Warning: RPC fetch failed ({exc})", C.YELLOW))

    if rpc_data is not None:
        if args.identity:
            try:
                rpc_data["identity_balance_sol"] = get_balance(args.rpc_url, args.identity)
            except Exception as exc:
                print(_color(f"Warning: identity balance fetch failed ({exc})", C.YELLOW))
        if args.vote_account:
            try:
                rpc_data["vote_balance_sol"] = get_balance(args.rpc_url, args.vote_account)
            except Exception as exc:
                print(_color(f"Warning: vote account balance fetch failed ({exc})", C.YELLOW))
        if args.withdrawer:
            try:
                rpc_data["withdrawer_balance_sol"] = get_balance(args.rpc_url, args.withdrawer)
            except Exception as exc:
                print(_color(f"Warning: withdrawer balance fetch failed ({exc})", C.YELLOW))
        if args.identity:
            try:
                rpc_data["block_production"] = get_block_production(args.rpc_url, args.identity)
            except Exception as exc:
                print(_color(f"Warning: block production fetch failed ({exc})", C.YELLOW))

        try:
            edata = get_epoch_data(args.rpc_url)
            rpc_data["epoch_data"] = edata
            rpc_data["vote_credits"] = compute_vote_credits_metrics(rpc_data, edata)
        except Exception as exc:
            print(_color(f"Warning: vote credits fetch failed ({exc})", C.YELLOW))

    report = render_full_report(
        lang=lang,
        log_data=log_data,
        rpc_data=rpc_data,
        identity=args.identity or args.vote_account,
    )
    print(report)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.full:
        _run_full_report(args)
    else:
        print(_color("Fetching Firedancer logs (last 24 h)…", C.DIM))
        lines = fetch_logs()
        if not lines:
            print(_color("No Firedancer log entries found in the last 24 hours.", C.YELLOW))
            sys.exit(0)
        data = parse_logs(lines)
        print_report(data)
