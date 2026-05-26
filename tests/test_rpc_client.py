"""Unit tests for firedancer_health_exporter.rpc_client."""

import json
from unittest.mock import MagicMock, patch

import pytest

from firedancer_health_exporter.rpc_client import (
    LAMPORTS_PER_SOL,
    get_epoch_data,
    get_validator_data,
)

VOTE = "VoteAccountTest11111111111111111111111111111"
IDENTITY = "ValidatorIdentityTest1111111111111111111111"
RPC = "http://127.0.0.1:8899"

_VALIDATOR_PAYLOAD = {
    "validators": [
        {
            "voteAccountPubkey": VOTE,
            "identityPubkey": IDENTITY,
            "activatedStake": 100_000 * LAMPORTS_PER_SOL,
            "skipRate": 5.0,
            "epochCredits": 42000,
            "commission": 5,
        }
    ]
}

_EPOCH_PAYLOAD = {"epoch": 700, "epochCompletedPercent": 73.5}


def _make_proc(stdout: str, returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = ""
    return m


def test_get_validator_data_success():
    with patch("firedancer_health_exporter.rpc_client.subprocess.run") as mock_run:
        mock_run.return_value = _make_proc(json.dumps(_VALIDATOR_PAYLOAD))
        result = get_validator_data(RPC, VOTE, IDENTITY)

    assert result["active_stake_sol"] == pytest.approx(100_000.0)
    assert result["skip_rate_percent"] == pytest.approx(5.0)
    assert result["credits"] == 42000
    assert result["commission"] == 5


def test_get_validator_data_not_found():
    payload = {"validators": []}
    with patch("firedancer_health_exporter.rpc_client.subprocess.run") as mock_run:
        mock_run.return_value = _make_proc(json.dumps(payload))
        with pytest.raises(RuntimeError, match="Validator not found"):
            get_validator_data(RPC, VOTE, IDENTITY)


def test_get_validator_data_json_parse_error():
    with patch("firedancer_health_exporter.rpc_client.subprocess.run") as mock_run:
        mock_run.return_value = _make_proc("not-valid-json")
        with pytest.raises(Exception):
            get_validator_data(RPC, VOTE, IDENTITY)
