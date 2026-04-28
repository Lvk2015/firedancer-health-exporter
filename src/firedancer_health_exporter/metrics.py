"""Prometheus metric definitions for the Firedancer Health Exporter."""

from prometheus_client import Gauge

_WINDOW = "24h"

# Log-based metrics
g_too_few_ticks = Gauge(
    "firedancer_too_few_ticks_total",
    f"TooFewTicks warnings in the last {_WINDOW}",
)
g_metrics_errors = Gauge(
    "firedancer_metrics_errors_total",
    f"Metrics-submit errors in the last {_WINDOW}",
)
g_critical_errors = Gauge(
    "firedancer_critical_errors_total",
    f"ERROR/PANIC/FATAL events in the last {_WINDOW}",
)
g_log_lines = Gauge(
    "firedancer_log_lines_total",
    f"Total log lines collected in the last {_WINDOW}",
)
g_log_scrape_duration = Gauge(
    "firedancer_exporter_log_scrape_duration_seconds",
    "Time taken to collect and parse journald logs",
)
g_log_scrape_errors = Gauge(
    "firedancer_exporter_log_scrape_errors_total",
    "Failed log-scrape attempts since exporter start",
)
g_last_log_scrape_ts = Gauge(
    "firedancer_exporter_last_log_scrape_timestamp",
    "Unix timestamp of the last successful log scrape",
)

# RPC-based metrics (populated only when --enable-rpc-metrics is passed)
g_active_stake = Gauge(
    "firedancer_validator_active_stake_sol",
    "Validator active stake in SOL (current epoch)",
)
g_skip_rate = Gauge(
    "firedancer_validator_skip_rate_percent",
    "Validator skip rate for current epoch, percent (0–100)",
)
g_credits = Gauge(
    "firedancer_validator_credits_total",
    "Vote credits earned in the current epoch",
)
g_commission = Gauge(
    "firedancer_validator_commission_percent",
    "Validator commission, percent (0–100)",
)
g_epoch_completed = Gauge(
    "firedancer_epoch_completed_percent",
    "Percentage of current epoch completed (0–100)",
)
g_rpc_scrape_duration = Gauge(
    "firedancer_exporter_rpc_scrape_duration_seconds",
    "Time taken to query Solana CLI for RPC metrics",
)
g_rpc_scrape_errors = Gauge(
    "firedancer_exporter_rpc_scrape_errors_total",
    "Failed RPC-scrape attempts since exporter start",
)
g_last_rpc_scrape_ts = Gauge(
    "firedancer_exporter_last_rpc_scrape_timestamp",
    "Unix timestamp of the last successful RPC scrape",
)
