"""Prometheus metric definitions for the Firedancer Health Exporter."""

import types

from prometheus_client import Gauge

_WINDOW = "24h"

# Log-based metrics (always registered)
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


def make_rpc_gauges() -> types.SimpleNamespace:
    """Create and register RPC Prometheus gauges. Call only when --enable-rpc-metrics is set."""
    return types.SimpleNamespace(
        _error_count=0,
        active_stake=Gauge(
            "firedancer_validator_active_stake_sol",
            "Validator active stake in SOL (current epoch)",
        ),
        skip_rate=Gauge(
            "firedancer_validator_skip_rate_percent",
            "Validator skip rate for current epoch, percent (0–100)",
        ),
        credits=Gauge(
            "firedancer_validator_credits_total",
            "Vote credits earned in the current epoch",
        ),
        commission=Gauge(
            "firedancer_validator_commission_percent",
            "Validator commission, percent (0–100)",
        ),
        epoch_completed=Gauge(
            "firedancer_epoch_completed_percent",
            "Percentage of current epoch completed (0–100)",
        ),
        scrape_duration=Gauge(
            "firedancer_exporter_rpc_scrape_duration_seconds",
            "Time taken to query Solana CLI for RPC metrics",
        ),
        scrape_errors=Gauge(
            "firedancer_exporter_rpc_scrape_errors_total",
            "Failed RPC-scrape attempts since exporter start",
        ),
        last_scrape_ts=Gauge(
            "firedancer_exporter_last_rpc_scrape_timestamp",
            "Unix timestamp of the last successful RPC scrape",
        ),
        vote_credits_efficiency=Gauge(
            "firedancer_vote_credits_efficiency_percent",
            "Vote credits efficiency: epochCredits / (slotsElapsed × 16) × 100",
        ),
        vote_credits_per_slot=Gauge(
            "firedancer_vote_credits_per_slot",
            "Vote credits earned per slot elapsed in the current epoch (max 16)",
        ),
        vote_credits_missed=Gauge(
            "firedancer_vote_credits_missed",
            "Vote credits missed vs theoretical max in the current epoch",
        ),
        vote_latency_slots=Gauge(
            "firedancer_vote_latency_slots",
            "Voting latency in slots (absoluteSlot − lastVoteSlot)",
        ),
    )
