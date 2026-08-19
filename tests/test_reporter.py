"""Unit tests for firedancer_health_exporter.reporter."""

from firedancer_health_exporter.i18n import t
from firedancer_health_exporter.reporter import render_full_report

_MINIMAL_LOG_DATA = {"too_few_ticks": 0, "metrics_errors": 0}


def _minimal_rpc_data(**overrides) -> dict:
    data = {
        "skip_rate_percent": 0.5,
        "active_stake_sol": 100.0,
        "commission": 0,
    }
    data.update(overrides)
    return data


def test_fee_rewards_zero_does_not_affect_overall_status():
    rpc_data = _minimal_rpc_data(fee_rewards_sol=0.0)

    report = render_full_report("en", _MINIMAL_LOG_DATA, rpc_data)

    assert t("en", "header_overall_ok") in report
    assert t("en", "rec_all_ok") in report


def test_fee_rewards_zero_does_not_add_recommendation():
    rpc_data = _minimal_rpc_data(fee_rewards_sol=0.0)

    report = render_full_report("en", _MINIMAL_LOG_DATA, rpc_data)

    assert t("en", "fee_rewards_rec_warn") not in report


def test_fee_rewards_metric_still_rendered_as_warn():
    rpc_data = _minimal_rpc_data(fee_rewards_sol=0.0)

    report = render_full_report("en", _MINIMAL_LOG_DATA, rpc_data)

    assert t("en", "fee_rewards_label") in report
    assert t("en", "fee_rewards_warn") in report
