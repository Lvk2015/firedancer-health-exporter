"""Unit tests for firedancer_health_exporter.log_parser."""

from firedancer_health_exporter.log_parser import parse_logs


def test_empty_input():
    result = parse_logs([])
    assert result == {"total": 0, "too_few_ticks": 0, "metrics_errors": 0, "critical": 0}


def test_only_too_few_ticks():
    lines = [
        "2024-04-27T10:00:01+0000 firedancer[123]: TooFewTicks detected",
        "2024-04-27T10:00:02+0000 firedancer[123]: TooFewTicks again",
    ]
    result = parse_logs(lines)
    assert result["too_few_ticks"] == 2
    assert result["critical"] == 0
    assert result["total"] == 2


def test_mixed_lines():
    lines = [
        "2024-04-27T10:00:01+0000 firedancer[1]: TooFewTicks detected",
        "2024-04-27T10:00:02+0000 firedancer[1]: metrics submit error occurred",
        "2024-04-27T10:00:03+0000 firedancer[1]: ERROR something broke",
        "2024-04-27T10:00:04+0000 firedancer[1]: normal info message",
        "2024-04-27T10:00:05+0000 firedancer[1]: PANIC fatal crash",
    ]
    result = parse_logs(lines)
    assert result["total"] == 5
    assert result["too_few_ticks"] == 1
    assert result["metrics_errors"] == 1
    assert result["critical"] == 2  # ERROR and PANIC, not the TooFewTicks line


def test_error_containing_too_few_ticks_not_counted_as_critical():
    """A line that contains both ERROR and TooFewTicks must not be counted as critical."""
    lines = [
        "2024-04-27T10:00:01+0000 firedancer[1]: ERROR TooFewTicks warning raised",
        "2024-04-27T10:00:02+0000 firedancer[1]: ERROR genuine critical failure",
    ]
    result = parse_logs(lines)
    assert result["too_few_ticks"] == 1
    assert result["critical"] == 1   # only the second line
    assert result["metrics_errors"] == 0
