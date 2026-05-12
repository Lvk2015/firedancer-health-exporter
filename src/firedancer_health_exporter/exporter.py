"""Main Prometheus exporter: scrape loops and HTTP server entry point."""

import argparse
import logging
import sys
import threading
import time
import types
from urllib.parse import urlparse

from .log_parser import fetch_logs, parse_logs
from .metrics import (
    g_last_log_scrape_ts,
    g_log_lines,
    g_log_scrape_duration,
    g_log_scrape_errors,
    g_metrics_errors,
    g_too_few_ticks,
    g_critical_errors,
    make_rpc_gauges,
)
from .rpc_client import get_epoch_data, get_validator_data

DEFAULT_PORT = 9100
DEFAULT_SCRAPE_SECS = 60
DEFAULT_RPC_URL = "http://127.0.0.1:8899"
DEFAULT_VOTE_ACCOUNT = ""
DEFAULT_IDENTITY = ""

_log_errors = 0


def scrape_logs() -> None:
    global _log_errors
    t0 = time.monotonic()
    try:
        lines = fetch_logs()
        data = parse_logs(lines)
        g_too_few_ticks.set(data["too_few_ticks"])
        g_metrics_errors.set(data["metrics_errors"])
        g_critical_errors.set(data["critical"])
        g_log_lines.set(data["total"])
        g_last_log_scrape_ts.set(time.time())
        logging.info(
            "log scrape ok | lines=%d too_few_ticks=%d metrics_errors=%d critical=%d",
            data["total"],
            data["too_few_ticks"],
            data["metrics_errors"],
            data["critical"],
        )
    except Exception as exc:
        _log_errors += 1
        g_log_scrape_errors.set(_log_errors)
        logging.error("log scrape failed: %s", exc)
    finally:
        g_log_scrape_duration.set(time.monotonic() - t0)


def scrape_rpc(rpc_url: str, vote_account: str, identity: str, gauges: types.SimpleNamespace) -> None:
    t0 = time.monotonic()
    try:
        vdata = get_validator_data(rpc_url, vote_account, identity)
        gauges.active_stake.set(vdata["active_stake_sol"])
        gauges.skip_rate.set(vdata["skip_rate_percent"])
        gauges.credits.set(vdata["credits"])
        gauges.commission.set(vdata["commission"])
        logging.info(
            "rpc validator | stake=%.2f SOL skip=%.2f%% credits=%d commission=%d%%",
            vdata["active_stake_sol"],
            vdata["skip_rate_percent"],
            vdata["credits"],
            vdata["commission"],
        )

        edata = get_epoch_data(rpc_url)
        gauges.epoch_completed.set(edata["completed_percent"])
        logging.info(
            "rpc epoch | epoch=%d completed=%.2f%%",
            edata["epoch"],
            edata["completed_percent"],
        )
        gauges.last_scrape_ts.set(time.time())
    except Exception as exc:
        gauges._error_count += 1
        gauges.scrape_errors.set(gauges._error_count)
        logging.error("rpc scrape failed: %s", exc)
    finally:
        gauges.scrape_duration.set(time.monotonic() - t0)


def collector_loop(
    interval: int,
    rpc_url: str | None,
    vote_account: str,
    identity: str,
    rpc_gauges: types.SimpleNamespace | None,
) -> None:
    while True:
        scrape_logs()
        if rpc_url and rpc_gauges is not None:
            scrape_rpc(rpc_url, vote_account, identity, rpc_gauges)
        time.sleep(interval)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Firedancer Health Prometheus Exporter",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--port", type=int, default=DEFAULT_PORT,
                   help="HTTP port to expose /metrics on")
    p.add_argument("--interval", type=int, default=DEFAULT_SCRAPE_SECS,
                   help="Scrape interval in seconds")

    rpc = p.add_argument_group("RPC metrics (disabled by default)")
    rpc.add_argument("--enable-rpc-metrics", action="store_true",
                     help="Enable Solana CLI / RPC metrics collection")
    rpc.add_argument("--rpc-url", default=DEFAULT_RPC_URL,
                     help="Solana RPC endpoint URL")
    rpc.add_argument("--vote-account", default=DEFAULT_VOTE_ACCOUNT,
                     help="Validator vote account public key")
    rpc.add_argument("--identity", default=DEFAULT_IDENTITY,
                     help="Validator identity public key")
    return p


def main() -> None:
    from prometheus_client import start_http_server

    parser = build_parser()
    args = parser.parse_args()

    if args.interval < 10:
        parser.error(f"--interval must be >= 10 seconds (got {args.interval})")

    if args.enable_rpc_metrics:
        if not args.vote_account:
            parser.error("--vote-account is required when --enable-rpc-metrics is set")
        if not args.identity:
            parser.error("--identity is required when --enable-rpc-metrics is set")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    rpc_url = args.rpc_url if args.enable_rpc_metrics else None
    rpc_gauges = make_rpc_gauges() if args.enable_rpc_metrics else None

    logging.info("Starting Firedancer Health Exporter on :%d", args.port)
    if rpc_url:
        logging.info("RPC metrics enabled | host=%s vote=%s", urlparse(rpc_url).netloc, args.vote_account)
    else:
        logging.info("RPC metrics disabled (pass --enable-rpc-metrics to enable)")

    start_http_server(args.port)

    scrape_logs()
    if rpc_url and rpc_gauges is not None:
        scrape_rpc(rpc_url, args.vote_account, args.identity, rpc_gauges)

    t = threading.Thread(
        target=collector_loop,
        args=(args.interval, rpc_url, args.vote_account, args.identity, rpc_gauges),
        daemon=True,
    )
    t.start()

    logging.info("Exporter ready — http://0.0.0.0:%d/metrics", args.port)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logging.info("Shutting down")
        sys.exit(0)
