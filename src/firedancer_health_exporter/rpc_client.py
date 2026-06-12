"""Solana CLI wrapper for fetching validator RPC metrics."""

import json
import subprocess

LAMPORTS_PER_SOL = 1_000_000_000
MAX_CREDITS_PER_SLOT = 16  # TVC: theoretical max vote credits per slot


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
        # skipRate is already 0–100; None means no blocks scheduled → treat as 0
        "skip_rate_percent": validator.get("skipRate") or 0.0,
        "credits": validator.get("epochCredits", 0),
        "commission": validator.get("commissionBps", validator.get("commission", 0)) / 100,
        "delinquent": validator.get("delinquent", False),
        "version": validator.get("version", ""),
        "last_vote_slot": validator.get("lastVote"),
    }


def get_epoch_data(rpc_url: str) -> dict:
    """Return current epoch info including slot counters needed for TVC metrics."""
    epoch = _run_solana(["epoch-info", "--url", rpc_url])
    return {
        "epoch": epoch["epoch"],
        "completed_percent": epoch["epochCompletedPercent"],
        "slot_index": epoch.get("slotIndex", 0),
        "slots_in_epoch": epoch.get("slotsInEpoch", 0),
        "absolute_slot": epoch.get("absoluteSlot", 0),
    }


def get_balance(rpc_url: str, pubkey: str) -> float:
    """Return balance in SOL for a pubkey (identity or vote account)."""
    data = _run_solana(["balance", pubkey, "--url", rpc_url])
    return data["lamports"] / LAMPORTS_PER_SOL


def compute_vote_credits_metrics(validator_data: dict, epoch_data: dict) -> dict:
    """Compute TVC-based vote credit metrics from already-fetched validator and epoch data.

    Returns a dict with efficiency_percent, credits_per_slot, missed_credits, and
    optionally latency_slots (only present when last_vote_slot is available).
    """
    epoch_credits = validator_data.get("credits", 0)
    slot_index = epoch_data.get("slot_index", 0)
    max_credits = slot_index * MAX_CREDITS_PER_SLOT

    result: dict = {
        "efficiency_percent": (epoch_credits / max_credits * 100) if max_credits > 0 else 0.0,
        "credits_per_slot": (epoch_credits / slot_index) if slot_index > 0 else 0.0,
        "missed_credits": max(0, max_credits - epoch_credits),
    }

    last_vote_slot = validator_data.get("last_vote_slot")
    absolute_slot = epoch_data.get("absolute_slot", 0)
    if last_vote_slot is not None and absolute_slot > last_vote_slot:
        result["latency_slots"] = absolute_slot - last_vote_slot

    return result


def get_block_production(rpc_url: str, identity: str) -> dict:
    """Return block production stats for the given identity in the current epoch."""
    data = _run_solana(["block-production", "--url", rpc_url])
    for leader in data.get("leaders", []):
        if leader.get("identityPubkey") == identity:
            assigned = leader["leaderSlots"]
            produced = leader["blocksProduced"]
            skipped = leader.get("skippedSlots", assigned - produced)
            skip_rate = (skipped / assigned * 100) if assigned > 0 else 0.0
            return {
                "assigned": assigned,
                "produced": produced,
                "skipped": skipped,
                "skip_rate": skip_rate,
            }
    raise RuntimeError(f"Identity {identity[:8]}… not found in block production data")
