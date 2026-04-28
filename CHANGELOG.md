# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-28

### Added
- **Log-based Prometheus metrics** via `journalctl -u firedancer`:
  - `firedancer_too_few_ticks_total` — TooFewTicks warning count (last 24 h)
  - `firedancer_metrics_errors_total` — `metrics submit error` line count (last 24 h)
  - `firedancer_critical_errors_total` — ERROR/PANIC/FATAL events (last 24 h); TooFewTicks lines are explicitly excluded from this counter
  - `firedancer_log_lines_total` — total log lines collected
  - Exporter self-metrics: scrape duration, error count, last-scrape timestamp
- **RPC metrics** (optional, enabled with `--enable-rpc-metrics`) via Solana CLI:
  - `firedancer_validator_active_stake_sol` — active stake in SOL
  - `firedancer_validator_skip_rate_percent` — block skip rate (0–100)
  - `firedancer_validator_credits_total` — epoch vote credits
  - `firedancer_validator_commission_percent` — validator commission
  - `firedancer_epoch_completed_percent` — current epoch progress
- **CLI diagnostic tool** (`firedancer-analyze`): colored one-shot terminal report with per-hour TooFewTicks histogram
- **systemd unit** (`deploy/firedancer-health-exporter.service`) with security hardening
- **Prometheus scrape config example** (`examples/prometheus.yml`)
- **Grafana alert rule examples** in README
- Configurable scrape interval (`--interval`, default 60 s) and HTTP port (`--port`, default 9100)
- `src/` layout with clean module separation: `metrics`, `log_parser`, `rpc_client`, `exporter`, `cli`
- Full test suite (pytest) with coverage for log parser and RPC client

[Unreleased]: https://github.com/antipov/firedancer-health-exporter/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/antipov/firedancer-health-exporter/releases/tag/v0.1.0
