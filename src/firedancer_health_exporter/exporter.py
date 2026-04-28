"""Main Prometheus exporter: scrape loops and HTTP server entry point."""

import argparse
import logging
import sys
import threading
import time

from .log_parser import fetch_logs, parse_logs
from .metrics import (
    g_active_stake,
    g_commission,
    g_credits,
    g_epoch_completed,
    g_last_log_scrape_ts,
    g_last_rpc_scrape_ts,
    g_log_lines,
    g_log_scrape_duration,
    g_log_scrape_errors,
    g_metrics_errors,
    g_rpc_scrape_duration,
    g_rpc_scrape_errors,
    g_skip_rate,
    g_too_few_ticks,
    g_critical_errors,
)
from .rpc_client import get_epoch_data, get_validator_data

DEFAULT_PORT = 9100
DEFAULT_SCRAPE_SECS = 60
DEFAULT_RPC_URL = "http://127.0.0.1:8899"
DEFAULT_VOTE_ACCOUNT = "H4EKYZB41o4iKGrkYF2Xy2rqamwSrvvacsBnYb5JUHB4"
DEFAULT_IDENTITY = "29ycd3N5WaikQ2SD3JzsyDunRHWssNfW9BvtCtcHNUYo"

_log_errors = 0
_rpc_errors = 0


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


def scrape_rpc(rpc_url: str, vote_account: str, identity: str) -> None:
    global _rpc_errors
    t0 = time.monotonic()
    try:
        vdata = get_validator_data(rpc_url, vote_account, identity)
        g_active_stake.set(vdata["active_stake_sol"])
        g_skip_rate.set(vdata["skip_rate_percent"])
        g_credits.set(vdata["credits"])
        g_commission.set(vdata["commission"])
        logging.info(
            "rpc validator | stake=%.2f SOL skip=%.2f%% credits=%d commission=%d%%",
            vdata["active_stake_sol"],
            vdata["skip_rate_percent"],
            vdata["credits"],
            vdata["commission"],
        )

        edata = get_epoch_data(rpc_url)
        g_epoch_completed.set(edata["completed_percent"])
        logging.info(
            "rpc epoch | epoch=%d completed=%.2f%%",
            edata["epoch"],
            edata["completed_percent"],
        )
        g_last_rpc_scrape_ts.set(time.time())
    except Exception as exc:
        _rpc_errors += 1
        g_rpc_scrape_errors.set(_rpc_errors)
        logging.error("rpc scrape failed: %s", exc)
    finally:
        g_rpc_scrape_duration.set(time.monotonic() - t0)


def collector_loop(
    interval: int, rpc_url: str | None, vote_account: str, identity: str
) -> None:
    while True:
        scrape_logs()
        if rpc_url:
            scrape_rpc(rpc_url, vote_account, identity)
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

    args = build_parser().parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    rpc_url = args.rpc_url if args.enable_rpc_metrics else None

    logging.info("Starting Firedancer Health Exporter on :%d", args.port)
    if rpc_url:
        logging.info("RPC metrics enabled | url=%s vote=%s", rpc_url, args.vote_account)
    else:
        logging.info("RPC metrics disabled (pass --enable-rpc-metrics to enable)")

    start_http_server(args.port)

    scrape_logs()
    if rpc_url:
        scrape_rpc(rpc_url, args.vote_account, args.identity)

    t = threading.Thread(
        target=collector_loop,
        args=(args.interval, rpc_url, args.vote_account, args.identity),
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
