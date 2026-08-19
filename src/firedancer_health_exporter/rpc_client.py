"""Solana CLI wrapper for fetching validator RPC metrics."""

import json
import subprocess
import urllib.error
import urllib.request

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


def _rpc_call(rpc_url: str, method: str, params: list, timeout: int = 30) -> object:
    """POST a JSON-RPC request straight to the Solana RPC endpoint.

    Only used for methods with no equivalent `solana` CLI subcommand (getInflationReward,
    getRecentPerformanceSamples) — everything else goes through `_run_solana` to stay
    consistent with how validator/epoch data is fetched.
    """
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(rpc_url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} request failed: {exc}") from exc
    if "error" in body:
        raise RuntimeError(body["error"].get("message", f"{method} returned an error"))
    return body["result"]


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


def compute_node_is_active(validator_data: dict) -> bool:
    """Return True if the validator is not delinquent and has active stake."""
    return not validator_data.get("delinquent", False) and validator_data.get("active_stake_sol", 0) > 0


def get_inflation_reward(rpc_url: str, vote_account: str, epoch: int) -> dict:
    """Return the vote account's inflation reward for the given epoch, via getInflationReward.

    Rewards are only posted once an epoch has fully completed and the reward distribution has
    run at the epoch boundary — callers should pass the previous (completed) epoch, not the
    current in-progress one, or this will return a zero amount.
    """
    result = _rpc_call(rpc_url, "getInflationReward", [[vote_account], {"epoch": epoch}])
    if not result or result[0] is None:
        return {"amount_sol": 0.0, "commission": None}
    entry = result[0]
    return {
        "amount_sol": entry.get("amount", 0) / LAMPORTS_PER_SOL,
        "commission": entry.get("commission"),
    }


def get_block_size_avg(rpc_url: str) -> float:
    """Return the cluster-wide average number of transactions per block.

    There is no RPC method for a single validator's average block size without fetching every
    block it produced (too expensive on a periodic scrape), so this reports the network-wide
    average over the most recent performance sample window as a proxy.
    """
    result = _rpc_call(rpc_url, "getRecentPerformanceSamples", [1])
    if not result:
        return 0.0
    sample = result[0]
    num_slots = sample.get("numSlots", 0)
    return (sample["numTransactions"] / num_slots) if num_slots > 0 else 0.0


def get_stake_account(rpc_url: str, stake_account: str) -> dict:
    """Return balance and delegation info for a stake account via `solana stake-account`."""
    data = _run_solana(["stake-account", stake_account, "--url", rpc_url])
    return {
        "total_balance_sol": data.get("accountBalance", 0) / LAMPORTS_PER_SOL,
        "delegated_sol": (data.get("delegatedStake") or 0) / LAMPORTS_PER_SOL,
        "delegated_vote_account": data.get("delegatedVoteAccountAddress"),
    }


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
