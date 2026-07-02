"""Rich diagnostic report renderer for firedancer-analyze --full."""

from .i18n import t

EMOJI = {"ok": "🟢", "warn": "🟡", "crit": "🔴"}
_SEP_HEAVY = "=" * 60
_SEP_LIGHT = "-" * 60


# ── threshold evaluators ──────────────────────────────────────────────────────

def _level_skip_rate(pct: float) -> str:
    if pct < 1.0:
        return "ok"
    if pct <= 5.0:
        return "warn"
    return "crit"


def _level_stake(sol: float) -> str:
    return "ok" if sol > 0 else "warn"


def _level_commission(pct: int) -> str:
    return "ok" if pct == 0 else "warn"


def _level_too_few_ticks(per_hour: float) -> str:
    if per_hour < 100:
        return "ok"
    if per_hour <= 500:
        return "warn"
    return "crit"


def _level_identity_balance(sol: float) -> str:
    if sol > 1.0:
        return "ok"
    if sol >= 0.5:
        return "warn"
    return "crit"


def _level_block_skip_rate(pct: float) -> str:
    if pct < 5.0:
        return "ok"
    if pct <= 10.0:
        return "warn"
    return "crit"


def _level_delinquent(is_del: bool) -> str:
    return "crit" if is_del else "ok"


def _level_metrics_errors(count: int) -> str:
    return "ok" if count == 0 else "warn"


def _level_credits_efficiency(pct: float) -> str:
    if pct > 98.0:
        return "ok"
    if pct >= 95.0:
        return "warn"
    return "crit"


def _level_withdrawer_balance(sol: float) -> str:
    if sol > 0.01:
        return "ok"
    if sol >= 0.001:
        return "warn"
    return "crit"


def _level_credits_per_slot(cps: float) -> str:
    if cps > 15.0:
        return "ok"
    if cps >= 13.0:
        return "warn"
    return "crit"


def _overall_level(levels: list[str]) -> str:
    if "crit" in levels:
        return "crit"
    if "warn" in levels:
        return "warn"
    return "ok"


# ── block builder ─────────────────────────────────────────────────────────────

def _metric_block(
    lang: str,
    label: str,
    value_str: str,
    level: str,
    status_key: str,
    info_key: str,
    norm_key: str,
) -> list[str]:
    icon = "✓" if level == "ok" else ("⚠" if level == "warn" else "✗")
    rows = [
        f"  {label}: {value_str} {EMOJI[level]}",
        f"  {icon} {t(lang, status_key)}",
        f"  ℹ {t(lang, info_key)}",
        f"  ℹ {t(lang, norm_key)}",
    ]
    return rows


# ── public API ────────────────────────────────────────────────────────────────

def render_full_report(
    lang: str,
    log_data: dict,
    rpc_data: dict | None,
    identity: str = "",
    version: str = "",
) -> str:
    out: list[str] = []
    levels: list[str] = []
    recs: list[str] = []
    metric_sections: list[list[str]] = []

    # ── RPC metrics ───────────────────────────────────────────────────────────
    if rpc_data:
        # Skip rate
        sr = rpc_data["skip_rate_percent"]
        sr_lv = _level_skip_rate(sr)
        levels.append(sr_lv)
        metric_sections.append(
            _metric_block(
                lang, t(lang, "skip_rate_label"),
                t(lang, "skip_rate_val", val=sr),
                sr_lv,
                f"skip_rate_{sr_lv}",
                "skip_rate_info", "skip_rate_norm",
            )
        )
        if sr_lv != "ok":
            recs.append(t(lang, f"skip_rate_rec_{sr_lv}"))

        # Stake
        stake = rpc_data["active_stake_sol"]
        stake_lv = _level_stake(stake)
        levels.append(stake_lv)
        metric_sections.append(
            _metric_block(
                lang, t(lang, "stake_label"),
                t(lang, "stake_val", val=stake),
                stake_lv,
                f"stake_{stake_lv}",
                "stake_info", "stake_norm",
            )
        )

        # Commission
        comm = rpc_data["commission"]
        comm_lv = _level_commission(comm)
        levels.append(comm_lv)
        metric_sections.append(
            _metric_block(
                lang, t(lang, "commission_label"),
                t(lang, "commission_val", val=comm),
                comm_lv,
                f"commission_{comm_lv}",
                "commission_info", "commission_norm",
            )
        )
        if comm_lv != "ok":
            recs.append(t(lang, f"commission_rec_{comm_lv}"))

        # Delinquent (optional field)
        if "delinquent" in rpc_data:
            is_del: bool = rpc_data["delinquent"]
            del_lv = _level_delinquent(is_del)
            levels.append(del_lv)
            del_val = t(lang, "delinquent_val_yes" if is_del else "delinquent_val_no")
            metric_sections.append(
                _metric_block(
                    lang, t(lang, "delinquent_label"),
                    del_val, del_lv,
                    f"delinquent_{del_lv}",
                    "delinquent_info", "delinquent_norm",
                )
            )
            if del_lv != "ok":
                recs.append(t(lang, f"delinquent_rec_{del_lv}"))

        # Identity balance
        if "identity_balance_sol" in rpc_data:
            id_bal = rpc_data["identity_balance_sol"]
            id_bal_lv = _level_identity_balance(id_bal)
            levels.append(id_bal_lv)
            metric_sections.append(
                _metric_block(
                    lang, t(lang, "identity_balance_label"),
                    t(lang, "identity_balance_val", val=id_bal),
                    id_bal_lv,
                    f"identity_balance_{id_bal_lv}",
                    "identity_balance_info", "identity_balance_norm",
                )
            )
            if id_bal_lv != "ok":
                recs.append(t(lang, f"identity_balance_rec_{id_bal_lv}"))

        # Vote account balance
        if "vote_balance_sol" in rpc_data:
            vote_bal = rpc_data["vote_balance_sol"]
            metric_sections.append(
                _metric_block(
                    lang, t(lang, "vote_balance_label"),
                    t(lang, "vote_balance_val", val=vote_bal),
                    "ok",
                    "vote_balance_ok",
                    "vote_balance_info", "vote_balance_norm",
                )
            )

        # Withdrawer balance
        if "withdrawer_balance_sol" in rpc_data:
            wd_bal = rpc_data["withdrawer_balance_sol"]
            wd_lv = _level_withdrawer_balance(wd_bal)
            levels.append(wd_lv)
            metric_sections.append(
                _metric_block(
                    lang, t(lang, "withdrawer_balance_label"),
                    t(lang, "withdrawer_balance_val", val=wd_bal),
                    wd_lv,
                    f"withdrawer_balance_{wd_lv}",
                    "withdrawer_balance_info", "withdrawer_balance_norm",
                )
            )
            if wd_lv != "ok":
                recs.append(t(lang, f"withdrawer_balance_rec_{wd_lv}"))

        # Block production (current epoch)
        if "block_production" in rpc_data:
            bp = rpc_data["block_production"]
            bp_lv = _level_block_skip_rate(bp["skip_rate"])
            levels.append(bp_lv)
            metric_sections.append(
                _metric_block(
                    lang, t(lang, "block_prod_label"),
                    t(lang, "block_prod_val",
                      assigned=bp["assigned"], produced=bp["produced"],
                      skipped=bp["skipped"], skip_rate=bp["skip_rate"]),
                    bp_lv,
                    f"block_prod_{bp_lv}",
                    "block_prod_info", "block_prod_norm",
                )
            )
            if bp_lv != "ok":
                recs.append(t(lang, f"block_prod_rec_{bp_lv}"))

        # Vote Credits (TVC)
        if "vote_credits" in rpc_data:
            vc = rpc_data["vote_credits"]

            eff = vc["efficiency_percent"]
            eff_lv = _level_credits_efficiency(eff)
            levels.append(eff_lv)
            metric_sections.append(
                _metric_block(
                    lang, t(lang, "vc_efficiency_label"),
                    t(lang, "vc_efficiency_val", val=eff),
                    eff_lv,
                    f"vc_efficiency_{eff_lv}",
                    "vc_efficiency_info", "vc_efficiency_norm",
                )
            )
            if eff_lv != "ok":
                recs.append(t(lang, f"vc_efficiency_rec_{eff_lv}"))

            cps = vc["credits_per_slot"]
            cps_lv = _level_credits_per_slot(cps)
            levels.append(cps_lv)
            metric_sections.append(
                _metric_block(
                    lang, t(lang, "vc_per_slot_label"),
                    t(lang, "vc_per_slot_val", val=cps),
                    cps_lv,
                    f"vc_per_slot_{cps_lv}",
                    "vc_per_slot_info", "vc_per_slot_norm",
                )
            )

            missed = vc["missed_credits"]
            metric_sections.append([
                f"  {t(lang, 'vc_missed_label')}: {t(lang, 'vc_missed_val', val=missed)} {EMOJI[eff_lv]}",
                f"  ℹ {t(lang, 'vc_missed_info')}",
            ])

            if "latency_slots" in vc:
                metric_sections.append([
                    f"  {t(lang, 'vc_latency_label')}: {t(lang, 'vc_latency_val', val=vc['latency_slots'])}",
                    f"  ℹ {t(lang, 'vc_latency_info')}",
                ])

        # Epoch progress
        if "epoch_data" in rpc_data:
            ed = rpc_data["epoch_data"]
            remaining = ed["slots_in_epoch"] - ed["slot_index"]
            metric_sections.append(
                _metric_block(
                    lang, t(lang, "epoch_label"),
                    t(lang, "epoch_val", epoch=ed["epoch"], pct=ed["completed_percent"], remaining=remaining),
                    "ok",
                    "epoch_ok",
                    "epoch_info", "epoch_norm",
                )
            )

        # Version from rpc_data (if present)
        if not version and rpc_data.get("version"):
            version = rpc_data["version"]
    else:
        metric_sections.append([f"  {t(lang, 'no_rpc')}"])

    # ── Log metrics ───────────────────────────────────────────────────────────
    tft = log_data.get("too_few_ticks", 0)
    tft_per_hour = tft / 24
    tft_lv = _level_too_few_ticks(tft_per_hour)
    levels.append(tft_lv)
    metric_sections.append(
        _metric_block(
            lang, t(lang, "too_few_ticks_label"),
            t(lang, "too_few_ticks_val", val=tft, per_hour=tft_per_hour),
            tft_lv,
            f"too_few_ticks_{tft_lv}",
            "too_few_ticks_info", "too_few_ticks_norm",
        )
    )
    if tft_lv != "ok":
        recs.append(t(lang, f"too_few_ticks_rec_{tft_lv}"))

    me = log_data.get("metrics_errors", 0)
    me_lv = _level_metrics_errors(me)
    levels.append(me_lv)
    metric_sections.append(
        _metric_block(
            lang, t(lang, "metrics_errors_label"),
            t(lang, "metrics_errors_val", val=me),
            me_lv,
            f"metrics_errors_{me_lv}",
            "metrics_errors_info", "metrics_errors_norm",
        )
    )
    if me_lv != "ok":
        recs.append(t(lang, "metrics_errors_rec_warn"))

    # ── Assemble output ───────────────────────────────────────────────────────
    overall = _overall_level(levels)

    out.append("")
    out.append(_SEP_HEAVY)
    out.append(f"  {t(lang, 'header_title')}")
    if identity:
        id_part = f"{identity[:8]}..."
        ver_part = f" | v{version}" if version else ""
        out.append(f"  {id_part}{ver_part}")
    out.append(_SEP_HEAVY)
    out.append("")
    out.append(f"  {EMOJI[overall]} {t(lang, f'header_overall_{overall}')}")
    out.append("")
    out.append(_SEP_LIGHT)

    for section in metric_sections:
        for row in section:
            out.append(row)
        out.append("")

    out.append(_SEP_LIGHT)

    rec_label = f"  💡 {t(lang, 'recommendations_label')}:"
    rec_text = t(lang, "rec_all_ok") if not recs else " ".join(recs)
    out.append(f"{rec_label} {rec_text}")
    out.append(_SEP_HEAVY)
    out.append("")

    return "\n".join(out)
