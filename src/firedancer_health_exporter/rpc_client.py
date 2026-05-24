"""Solana CLI wrapper for fetching validator RPC metrics."""

import json
import subprocess

LAMPORTS_PER_SOL = 1_000_000_000


def _run_solana(args_list: list[str], timeout: int = 30) -> dict:
    result = subprocess.run(
        ["solana"] + args_list + ["--output", "json"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"exit code {result.returncode}")
    return json.loads(result.stdout)


def get_validator_data(rpc_url: str, vote_account: str, identity: str) -> dict:
    """Return stake/skip/credits/commission for the given validator.

    Raises RuntimeError if the validator is not found in the response.
    """
    data = _run_solana(["validators", "--url", rpc_url])

    validator = None
    for v in data.get("validators", []):
        if v.get("voteAccountPubkey") == vote_account or v.get("identityPubkey") == identity:
            validator = v
            break

    if validator is None:
        raise RuntimeError(
            f"Validator not found in response "
            f"(vote={vote_account[:8]}… identity={identity[:8]}…)"
        )

    return {
        "active_stake_sol": validator["activatedStake"] / LAMPORTS_PER_SOL,
        # skipRate is 0.0–1.0; None means no blocks scheduled → treat as 0
        "skip_rate_percent": (validator.get("skipRate") or 0.0) * 100,
        "credits": validator.get("epochCredits", 0),
        "commission": validator["commission"],
        "delinquent": validator.get("delinquent", False),
        "version": validator.get("version", ""),
    }


def get_epoch_data(rpc_url: str) -> dict:
    """Return current epoch number and completion percentage."""
    epoch = _run_solana(["epoch-info", "--url", rpc_url])
    return {
        "epoch": epoch["epoch"],
        "completed_percent": epoch["epochCompletedPercent"],
    }
