# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.2] - 2026-05-26

### Fixed

- **Skip rate bug**: `rpc_client` no longer multiplies `skipRate` by 100 — the RPC already returns the value in percent (0–100), so the previous code inflated values 100× (e.g. 13.33% → 1333.33%).

## [0.3.1] - 2026-05-26

### Fixed

- **TooFewTicks threshold bug**: thresholds now apply to the per-hour average (`total / 24`) instead of the raw 24 h sum. Display shows both numbers: `505 total 24h (~21/hr)`.

### Added

- **Node balance** (`--identity`): identity keypair SOL balance with thresholds — > 1 SOL 🟢, 0.5–1 SOL 🟡, < 0.5 SOL 🔴. Low balance triggers a recommendation.
- **Vote account balance** (`--vote-account`): accumulated rewards on the vote account, shown as an informational metric.
- **Block production (current epoch)** (`--identity`): assigned / produced / skipped slot counts with skip rate — < 5% 🟢, 5–10% 🟡, > 10% 🔴.
- `rpc_client.get_balance(rpc_url, pubkey)` — returns SOL balance for any pubkey.
- `rpc_client.get_block_production(rpc_url, identity)` — returns epoch block production stats filtered by identity.
- i18n strings (EN + RU) for all new metrics.

## [0.3.0] - 2026-05-24

### Added

- **`firedancer-analyze --full`**: rich diagnostic report with per-metric explanations, normal-range guidance, and actionable recommendations. Works with or without RPC access.
- **`firedancer-analyze --lang ru`**: full Russian language support for all report text (`--lang en` remains the default).
- **Emoji status indicators** across the full report: 🟢 healthy, 🟡 attention, 🔴 action required — meaningful thresholds per metric:
  - Skip rate: < 1% 🟢 / 1–5% 🟡 / > 5% 🔴
  - TooFewTicks (24 h): < 100 🟢 / 100–500 🟡 / > 500 🔴
  - Commission: 0% 🟢 / > 0% 🟡
  - Delinquent: no 🟢 / yes 🔴
- **`--rpc-url`, `--vote-account`, `--identity`** flags on `firedancer-analyze` for optional on-demand RPC metric fetch (stake, skip rate, commission, delinquent status, version).
- **`src/firedancer_health_exporter/reporter.py`**: standalone report-rendering module (testable, language-agnostic).
- **`src/firedancer_health_exporter/i18n.py`**: all user-facing strings in EN and RU; easy to extend with additional languages.
- `rpc_client.get_validator_data` now returns `delinquent` (bool) and `version` (str) fields.

## [0.1.2] - 2026-05-12

### Fixed

- **RPC URL logging**: log now outputs only the hostname (`netloc` via `urllib.parse.urlparse`) instead of the full URL, avoiding accidental exposure of credentials or internal addresses.
- **CLI validation**: `--interval` now requires a value >= 10 seconds; passing a lower value produces a clear error message instead of silently allowing dangerously short scrape intervals.

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

[Unreleased]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.3.2...HEAD
[0.3.2]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.1.2...v0.3.0
[0.1.2]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.1.0...v0.1.2
[0.1.0]: https://github.com/Lvk2015/firedancer-health-exporter/releases/tag/v0.1.0
