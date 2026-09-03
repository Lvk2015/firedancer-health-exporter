# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.3] - 2026-09-03

### Added

- **`--log-window` CLI flag**: both `firedancer-exporter` and `firedancer-analyze` now accept `--log-window HOURS` (default: 24) to control how many hours of journald logs are fetched per scrape/run, instead of always hardcoding 24h.

## [0.6.2] - 2026-08-20

### Added

- **Exporter version in report header**: `firedancer-analyze --full` now shows the exporter's own version (`exporter vX.Y.Z`) next to the node version in the report header.

## [0.6.1] - 2026-08-19

### Fixed

- **`fee_rewards` is now informational only**: no longer factored into overall report status or recommendations — a zero/missing reward for the previous epoch was triggering unnecessary warnings.
- **Testnet note for `fee_rewards`/`epoch_income`**: EN/RU report text now explains that testnet always reports 0 inflation reward by design, so it isn't mistaken for an issue.

### Added

- Reporter tests covering the new metrics added in v0.6.0 (`tests/test_reporter.py`).

## [0.6.0] - 2026-08-19

### Added

- **`solana_node_is_active`** Prometheus Gauge — 1 if the validator is not delinquent and has active stake, 0 otherwise.
- **`solana_validator_fee_rewards_sol`** / **`solana_validator_epoch_income_sol`** Prometheus Gauges — vote account inflation reward (`getInflationReward`) for the most recently completed epoch, in SOL.
- **`solana_validator_block_size_avg`** Prometheus Gauge — cluster-wide average transactions per block over the most recent performance sample (`getRecentPerformanceSamples`); a proxy, not filtered to this validator.
- **`--stake-account <PUBKEY>`** option for `firedancer-exporter` and `firedancer-analyze` — optional stake account public key.
- **`solana_stake_account_balance_sol`** / **`solana_stake_account_delegated_sol`** Prometheus Gauges — total and actively delegated balance of the configured stake account; only published when `--stake-account` is passed.
- **New report sections in `firedancer-analyze --full`** for node active status, fee rewards, epoch income, block size average, and stake account balance/delegation — full EN and RU i18n support.
- `rpc_client._rpc_call()` — direct JSON-RPC POST helper for `getInflationReward` and `getRecentPerformanceSamples`, which have no equivalent `solana` CLI subcommand.
- `rpc_client.compute_node_is_active()`, `get_inflation_reward()`, `get_block_size_avg()`, `get_stake_account()`.

## [0.4.1] - 2026-05-28

### Added

- **`--withdrawer <PUBKEY>`** option for `firedancer-exporter` and `firedancer-analyze` — optional withdrawer account public key.
- **`firedancer_withdrawer_balance_sol`** Prometheus Gauge — SOL balance of the withdrawer account; only published when `--withdrawer` is passed to the exporter.
- **Withdrawer Balance section in `firedancer-analyze --full`** — displays balance with emoji thresholds (> 0.01 SOL 🟢, 0.001–0.01 SOL 🟡, < 0.001 SOL 🔴); warns to top up for commission changes; full EN and RU i18n support.

## [0.4.0] - 2026-05-28

### Added

- **TVC vote credit metrics** — four new Prometheus gauges derived from the existing `getVoteAccounts` RPC call (no extra RPC round-trips):
  - `firedancer_vote_credits_efficiency_percent` — `epochCredits / (slotsElapsed × 16) × 100`; thresholds: > 98% 🟢, 95–98% 🟡, < 95% 🔴
  - `firedancer_vote_credits_per_slot` — `epochCredits / epochSlotsElapsed`; thresholds: > 15 🟢, 13–15 🟡, < 13 🔴
  - `firedancer_vote_credits_missed` — `maxEpochCredits − epochCredits` (absolute missed credits since epoch start)
  - `firedancer_vote_latency_slots` — `absoluteSlot − lastVoteSlot`; only published when `lastVote` is present in the RPC response
- **Vote Credits section in `firedancer-analyze --full`** — displays efficiency%, credits/slot (with emoji thresholds), missed credits count, and optional vote latency; full EN and RU i18n support
- `rpc_client.compute_vote_credits_metrics(validator_data, epoch_data)` — pure function; easy to unit-test independently of RPC calls
- `rpc_client.get_epoch_data` now also returns `slot_index`, `slots_in_epoch`, and `absolute_slot` fields

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

[Unreleased]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.6.1...HEAD
[0.6.1]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.4.1...v0.6.0
[0.4.0]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.1.2...v0.3.0
[0.1.2]: https://github.com/Lvk2015/firedancer-health-exporter/compare/v0.1.0...v0.1.2
[0.1.0]: https://github.com/Lvk2015/firedancer-health-exporter/releases/tag/v0.1.0
