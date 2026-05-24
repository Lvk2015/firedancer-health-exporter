"""Internationalization strings for firedancer-analyze --full output."""

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # Header
        "header_title": "FIREDANCER NODE STATUS",
        "header_overall_ok": "OVERALL STATUS: NODE IS HEALTHY",
        "header_overall_warn": "OVERALL STATUS: ATTENTION REQUIRED",
        "header_overall_crit": "OVERALL STATUS: ACTION REQUIRED",
        # Skip rate
        "skip_rate_label": "Skip Rate",
        "skip_rate_val": "{val:.2f}%",
        "skip_rate_ok": "Excellent! Node is confirming all assigned leader blocks.",
        "skip_rate_warn": "Skip rate is elevated — monitor closely.",
        "skip_rate_crit": "High skip rate — investigate immediately.",
        "skip_rate_info": "What this is: percentage of leader slots missed by this validator.",
        "skip_rate_norm": "Normal: < 1%. Above 5% is a serious problem.",
        "skip_rate_rec_warn": "Check node connectivity and CPU/disk load.",
        "skip_rate_rec_crit": "Urgent: check hardware, network, and Firedancer logs for errors.",
        # Stake
        "stake_label": "Stake",
        "stake_val": "{val:,.0f} SOL",
        "stake_ok": "Foundation is delegating stake — node meets SFDP requirements.",
        "stake_warn": "No active stake. Check SFDP eligibility requirements.",
        "stake_info": "What this is: total SOL delegated to this validator.",
        "stake_norm": "Normal: any value > 0 means the node is active.",
        # Commission
        "commission_label": "Commission",
        "commission_val": "{val}%",
        "commission_ok": "Meets SFDP program requirements.",
        "commission_warn": "Commission above 0% — verify SFDP requirements.",
        "commission_info": "What this is: percentage of staking rewards taken by the validator.",
        "commission_norm": "SFDP requires 0% commission.",
        "commission_rec_warn": "Consider lowering commission to 0% to meet SFDP requirements.",
        # TooFewTicks
        "too_few_ticks_label": "TooFewTicks",
        "too_few_ticks_val": "{val:,}",
        "too_few_ticks_ok": "No block quality issues from other validators.",
        "too_few_ticks_warn": "Other validators sent blocks with quality issues — monitor rate.",
        "too_few_ticks_crit": "High rate of malformed blocks from the network.",
        "too_few_ticks_info": "What this is: blocks received from other validators with too few ticks.",
        "too_few_ticks_norm": "Normal on testnet. No action needed if < 500 per hour.",
        "too_few_ticks_rec_warn": "Normal for testnet. No action needed if < 500/hour.",
        "too_few_ticks_rec_crit": "Investigate network peers. Consider updating Firedancer.",
        # Delinquent
        "delinquent_label": "Delinquent",
        "delinquent_val_yes": "YES",
        "delinquent_val_no": "NO",
        "delinquent_ok": "Node is voting and participating normally.",
        "delinquent_crit": "Node is delinquent — not voting! Immediate action required.",
        "delinquent_info": "What this is: a delinquent validator has stopped voting on the network.",
        "delinquent_norm": "Normal: not delinquent. Any delinquency requires immediate action.",
        "delinquent_rec_crit": "Restart Firedancer immediately. Check disk, memory, and network.",
        # Metrics errors
        "metrics_errors_label": "Metrics Errors",
        "metrics_errors_val": "{val}",
        "metrics_errors_ok": "No metrics submission errors.",
        "metrics_errors_warn": "Metrics submission errors detected — Prometheus may have gaps.",
        "metrics_errors_info": "What this is: failed attempts to submit metrics.",
        "metrics_errors_norm": "Normal: 0. Any errors may cause gaps in monitoring data.",
        "metrics_errors_rec_warn": "Check Prometheus connectivity and exporter configuration.",
        # Footer
        "recommendations_label": "RECOMMENDATIONS",
        "rec_all_ok": "Node is in excellent condition.",
        "no_rpc": "(RPC metrics unavailable — pass --rpc-url and --vote-account/--identity to enable)",
        "no_logs": "(no log entries found in the last 24 hours)",
    },
    "ru": {
        # Header
        "header_title": "СОСТОЯНИЕ НОДЫ FIREDANCER",
        "header_overall_ok": "ОБЩИЙ СТАТУС: НОДА РАБОТАЕТ НОРМАЛЬНО",
        "header_overall_warn": "ОБЩИЙ СТАТУС: ТРЕБУЕТ ВНИМАНИЯ",
        "header_overall_crit": "ОБЩИЙ СТАТУС: ТРЕБУЕТ ДЕЙСТВИЙ",
        # Skip rate
        "skip_rate_label": "Skip Rate",
        "skip_rate_val": "{val:.2f}%",
        "skip_rate_ok": "Отлично! Нода подтверждает все назначенные блоки.",
        "skip_rate_warn": "Skip rate повышен — следите за показателем.",
        "skip_rate_crit": "Высокий skip rate — немедленно разберитесь с проблемой.",
        "skip_rate_info": "Что это: процент пропущенных слотов лидера.",
        "skip_rate_norm": "Норма: < 1%. Выше 5% — серьёзная проблема.",
        "skip_rate_rec_warn": "Проверьте сетевое соединение и нагрузку на CPU/диск.",
        "skip_rate_rec_crit": "Срочно: проверьте железо, сеть и логи Firedancer на ошибки.",
        # Stake
        "stake_label": "Стейк",
        "stake_val": "{val:,.0f} SOL",
        "stake_ok": "Foundation делегирует стейк — нода соответствует SFDP.",
        "stake_warn": "Активного стейка нет. Проверьте требования SFDP.",
        "stake_info": "Что это: общее количество SOL, делегированных валидатору.",
        "stake_norm": "Норма: любое значение > 0 означает, что нода активна.",
        # Commission
        "commission_label": "Комиссия",
        "commission_val": "{val}%",
        "commission_ok": "Соответствует требованиям SFDP программы.",
        "commission_warn": "Комиссия выше 0% — проверьте требования SFDP.",
        "commission_info": "Что это: процент вознаграждения за стейкинг, удерживаемый валидатором.",
        "commission_norm": "SFDP требует комиссию 0%.",
        "commission_rec_warn": "Рассмотрите снижение комиссии до 0% для соответствия SFDP.",
        # TooFewTicks
        "too_few_ticks_label": "TooFewTicks",
        "too_few_ticks_val": "{val:,}",
        "too_few_ticks_ok": "Проблем с качеством блоков от других валидаторов нет.",
        "too_few_ticks_warn": "Другие валидаторы прислали блоки с ошибками. Следите за частотой.",
        "too_few_ticks_crit": "Высокая частота некорректных блоков от сети.",
        "too_few_ticks_info": "Что это: блоки от других валидаторов с недостаточным количеством тиков.",
        "too_few_ticks_norm": "Норма для testnet. Действий не требуется если меньше 500 в час.",
        "too_few_ticks_rec_warn": "Нормально для testnet. Действий не требуется если < 500/час.",
        "too_few_ticks_rec_crit": "Проверьте пиров в сети. Рассмотрите обновление Firedancer.",
        # Delinquent
        "delinquent_label": "Delinquent",
        "delinquent_val_yes": "ДА",
        "delinquent_val_no": "НЕТ",
        "delinquent_ok": "Нода голосует и участвует в работе сети нормально.",
        "delinquent_crit": "Нода delinquent — не голосует! Требуется немедленное действие.",
        "delinquent_info": "Что это: delinquent валидатор прекратил голосование в сети.",
        "delinquent_norm": "Норма: не delinquent. Любой delinquent требует немедленного внимания.",
        "delinquent_rec_crit": "Немедленно перезапустите Firedancer. Проверьте диск, память и сеть.",
        # Metrics errors
        "metrics_errors_label": "Ошибки метрик",
        "metrics_errors_val": "{val}",
        "metrics_errors_ok": "Ошибок отправки метрик нет.",
        "metrics_errors_warn": "Обнаружены ошибки отправки метрик — в Prometheus могут быть пробелы.",
        "metrics_errors_info": "Что это: неудачные попытки отправить метрики.",
        "metrics_errors_norm": "Норма: 0. Любые ошибки могут вызвать пробелы в мониторинге.",
        "metrics_errors_rec_warn": "Проверьте связь с Prometheus и конфигурацию экспортера.",
        # Footer
        "recommendations_label": "РЕКОМЕНДАЦИИ",
        "rec_all_ok": "Нода в отличном состоянии.",
        "no_rpc": "(RPC-метрики недоступны — передайте --rpc-url и --vote-account/--identity для включения)",
        "no_logs": "(записей в логах за последние 24 часа не найдено)",
    },
}


def t(lang: str, key: str, **kw: object) -> str:
    """Return translated string, formatting any keyword placeholders."""
    text = _STRINGS.get(lang, _STRINGS["en"]).get(key) or _STRINGS["en"].get(key, key)
    return text.format(**kw) if kw else text
