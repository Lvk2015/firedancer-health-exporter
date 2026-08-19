# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Prometheus exporter for Firedancer Solana validator nodes. It reads `journalctl -u firedancer` logs and optionally shells out to the `solana` CLI for RPC-based validator/epoch metrics, exposing everything on `:9100/metrics`. It also ships a standalone CLI diagnostic tool (`firedancer-analyze`).

## Commands

```bash
# Setup (editable install with test deps)
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest
pytest tests/test_log_parser.py::test_mixed_lines   # single test
pytest --cov=src --cov-report=html                  # with coverage

# Run the exporter / CLI locally
firedancer-exporter                                  # requires journalctl -u firedancer to exist
firedancer-exporter --enable-rpc-metrics --rpc-url <url> --vote-account <pk> --identity <pk>
firedancer-analyze                                   # one-shot log report
firedancer-analyze --full --lang ru --vote-account <pk> --identity <pk>  # full colored report, RU/EN
```

There is no lint/format tooling configured in this repo (no ruff/black/flake8 config) — don't invent commands for it.

CI (`.github/workflows/test.yml`) runs `pytest` on Python 3.10/3.11/3.12 and uploads coverage from 3.12 only.

## Architecture

Two entry points share the same data-collection code but diverge in how they render it:

- `firedancer-exporter` → `exporter.py:main()` — long-running Prometheus HTTP server (`prometheus_client.start_http_server`). A background thread (`collector_loop`) calls `scrape_logs()` and, if enabled, `scrape_rpc()` on a fixed interval, setting `Gauge` values defined in `metrics.py`. All gauges are created once at import time (log gauges) or once via `make_rpc_gauges()` at startup (RPC gauges) — there is no per-scrape re-registration.
- `firedancer-analyze` → `cli.py:main()` — one-shot process. Default mode reprints a lightweight colored terminal summary using its own local copies of the regexes/fetch/parse logic (duplicated from `log_parser.py`, not imported from it — keep both in sync if you touch parsing rules). `--full` mode instead calls `reporter.render_full_report()` for a richer bilingual (EN/RU) report with per-metric health thresholds and recommendations.

Core modules under `src/firedancer_health_exporter/`:
- `log_parser.py` — canonical journald log fetch (`fetch_logs`) and parse (`parse_logs`) logic used by the exporter. Classifies lines into `too_few_ticks`, `metrics_errors`, and `critical` (ERROR/PANIC/FATAL) counts; a line matching TooFewTicks is *never* also counted as critical, even if it contains ERROR/PANIC/FATAL — see `test_error_containing_too_few_ticks_not_counted_as_critical`.
- `rpc_client.py` — thin wrapper around the `solana` CLI (`solana validators`, `solana epoch-info`, `solana balance`, `solana block-production`, always with `--output json`), not the JSON-RPC HTTP API directly. `compute_vote_credits_metrics()` derives TVC (theoretical vote credits) efficiency/latency stats from already-fetched validator + epoch data — it's pure computation, no I/O, so test it without mocking subprocess.
- `metrics.py` — all Prometheus `Gauge` definitions. Log-based gauges are always registered; RPC gauges only exist if `--enable-rpc-metrics` is passed (`make_rpc_gauges()` returns a `SimpleNamespace` bundle, including an `_error_count` counter for the error gauge).
- `reporter.py` — builds the `--full` diagnostic report. Each metric has a `_level_*` threshold function returning `"ok" | "warn" | "crit"`, feeding both an emoji/status line and (if not ok) an entry in the recommendations list. Overall status is the worst level across all evaluated metrics. All user-facing strings are looked up via `i18n.t(lang, key, **fmt_args)`.
- `i18n.py` — flat `dict[lang][key] -> format string` table for `en`/`ru`. When adding a new metric to `reporter.py`, add matching `_label`, `_val`, `_{level}`, `_info`, `_norm` (and `_rec_warn`/`_rec_crit` if actionable) keys for **both** languages, or the report will raise `KeyError`.

### Data flow for RPC metrics

`get_validator_data()` + `get_epoch_data()` are fetched independently, then combined by `compute_vote_credits_metrics(vdata, edata)` — this combining step is duplicated at both call sites (`exporter.py:scrape_rpc` and `cli.py:_run_full_report`) rather than fetched together, since the exporter only needs gauge values while the CLI also wants raw epoch/validator dicts for other report sections.

### Errors and resilience

Both scrape functions (`scrape_logs`, `scrape_rpc`) catch broad `Exception`, increment an error-count gauge, and log — they never raise, since a single failed scrape shouldn't crash the long-running exporter process. The CLI's `--full` mode instead catches per-field (balance, block production, vote credits) so one failing RPC call degrades that section of the report rather than aborting it.

## Deployment

`deploy/firedancer-health-exporter.service` is a hardened systemd unit (`ProtectSystem=strict`, `NoNewPrivileges`, journal-only read access via `BindReadOnlyPaths`). `examples/prometheus.yml` and `examples/grafana-dashboard.json` are reference configs referenced from README — keep metric names in sync across `metrics.py`, the Grafana dashboard JSON, and the README metrics tables if you rename or add a gauge.

`build/` contains a stale copy of the package (from a prior `pip install`/build) — it is not the source of truth; always edit under `src/firedancer_health_exporter/`.
