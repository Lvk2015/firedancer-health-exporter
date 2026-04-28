# firedancer-health-exporter

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Prometheus exporter for [Firedancer](https://github.com/firedancer-io/firedancer) Solana validator nodes.
Reads `journalctl -u firedancer` and optionally queries the Solana CLI to expose health metrics on `:9100/metrics`.

---

## Features

- **Log-based metrics** — TooFewTicks warnings, metrics-submit errors, ERROR/PANIC/FATAL events, all scoped to the last 24 hours
- **RPC metrics** (optional) — active stake, skip rate, epoch credits, commission, epoch progress via the Solana CLI
- **CLI diagnostic tool** — colored one-shot terminal report with per-hour TooFewTicks histogram
- **systemd service** with security hardening (NoNewPrivileges, ProtectSystem, PrivateTmp)
- Configurable port, scrape interval, and RPC endpoint

---

## Installation

### From PyPI (once published)

```bash
pip install firedancer-health-exporter
```

### From source

```bash
git clone https://github.com/antipov/firedancer-health-exporter.git
cd firedancer-health-exporter
pip install .
```

**Requirements:**
- Python 3.10+
- Linux with systemd (`journalctl`)
- Read access to the Firedancer journal (add your user to the `systemd-journal` group)
- `prometheus_client >= 0.19`

---

## Quick Start

```bash
# Install dependency
pip install prometheus_client

# Run the exporter (log metrics only)
firedancer-exporter

# Metrics available at:
curl http://localhost:9100/metrics | grep firedancer_

# Enable RPC metrics
firedancer-exporter \
  --enable-rpc-metrics \
  --rpc-url https://api.mainnet-beta.solana.com \
  --vote-account <YOUR_VOTE_PUBKEY> \
  --identity  <YOUR_IDENTITY_PUBKEY>

# One-shot CLI diagnostic report
firedancer-analyze
```

---

## Configuration

| Flag | Default | Description |
|---|---|---|
| `--port` | `9100` | HTTP port to expose `/metrics` on |
| `--interval` | `60` | Scrape interval in seconds |
| `--enable-rpc-metrics` | off | Enable Solana CLI / RPC metrics |
| `--rpc-url` | `http://127.0.0.1:8899` | Solana RPC endpoint |
| `--vote-account` | — | Validator vote account public key |
| `--identity` | — | Validator identity public key |

---

## Metrics

### Log-based (always active)

| Metric | Type | Description |
|---|---|---|
| `firedancer_too_few_ticks_total` | Gauge | TooFewTicks warnings in last 24 h |
| `firedancer_metrics_errors_total` | Gauge | `metrics submit error` lines in last 24 h |
| `firedancer_critical_errors_total` | Gauge | ERROR/PANIC/FATAL events in last 24 h (TooFewTicks lines excluded) |
| `firedancer_log_lines_total` | Gauge | Total log lines collected |
| `firedancer_exporter_log_scrape_duration_seconds` | Gauge | Time to collect and parse logs |
| `firedancer_exporter_log_scrape_errors_total` | Gauge | Failed log-scrape attempts since start |
| `firedancer_exporter_last_log_scrape_timestamp` | Gauge | Unix timestamp of last successful log scrape |

### RPC-based (with `--enable-rpc-metrics`)

| Metric | Type | Description |
|---|---|---|
| `firedancer_validator_active_stake_sol` | Gauge | Active stake in SOL |
| `firedancer_validator_skip_rate_percent` | Gauge | Block skip rate, 0–100 |
| `firedancer_validator_credits_total` | Gauge | Vote credits this epoch |
| `firedancer_validator_commission_percent` | Gauge | Validator commission, 0–100 |
| `firedancer_epoch_completed_percent` | Gauge | Current epoch progress, 0–100 |
| `firedancer_exporter_rpc_scrape_duration_seconds` | Gauge | Time for RPC query |
| `firedancer_exporter_rpc_scrape_errors_total` | Gauge | Failed RPC-scrape attempts |
| `firedancer_exporter_last_rpc_scrape_timestamp` | Gauge | Unix timestamp of last successful RPC scrape |

---

## Prometheus Config

```yaml
scrape_configs:
  - job_name: firedancer
    static_configs:
      - targets: ['<validator-ip>:9100']
    scrape_interval: 60s
```

See [`examples/prometheus.yml`](examples/prometheus.yml) for a complete example.

---

## Grafana Alert Examples

```yaml
groups:
  - name: firedancer
    rules:
      - alert: FiredancerTooFewTicksHigh
        expr: firedancer_too_few_ticks_total > 20
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High TooFewTicks count on {{ $labels.instance }}"
          description: "{{ $value }} TooFewTicks events in the last 24 h"

      - alert: FiredancerCriticalError
        expr: firedancer_critical_errors_total > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Firedancer ERROR/PANIC/FATAL on {{ $labels.instance }}"

      - alert: FiredancerHighSkipRate
        expr: firedancer_validator_skip_rate_percent > 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Validator skip rate above 10% on {{ $labels.instance }}"
```

---

## Production Install (systemd)

```bash
# 1. Install
sudo mkdir -p /opt/firedancer-health-exporter
pip install firedancer-health-exporter --target /opt/firedancer-health-exporter

# 2. Add firedancer user to systemd-journal group
sudo usermod -aG systemd-journal firedancer

# 3. Install and enable systemd service
sudo cp deploy/firedancer-health-exporter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now firedancer-health-exporter

# 4. Verify
sudo systemctl status firedancer-health-exporter
curl -s http://localhost:9100/metrics | grep firedancer_
```

---

## Development

```bash
git clone https://github.com/antipov/firedancer-health-exporter.git
cd firedancer-health-exporter
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
pytest --cov=src --cov-report=html   # with coverage report
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Add tests for new functionality
4. Run `pytest` and ensure all tests pass
5. Open a Pull Request

---

## License

MIT — see [LICENSE](LICENSE).
