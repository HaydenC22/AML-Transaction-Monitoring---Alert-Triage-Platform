"""
Generates a PaySim-schema-compatible synthetic mobile-money transaction dataset.

Why generated rather than downloaded: the real PaySim dataset is Kaggle-hosted and
requires an authenticated Kaggle API token to fetch programmatically, which conflicts
with this project's "docker compose up, no signup" goal (see docs/adr/0004). This
generator reproduces PaySim's exact column schema and its documented quirks (merchant
destinations carry no balance history; fraud transactions tend to zero out destination
balances) using a seeded, fully reproducible simulation, so no redistribution or
licensing question is in play. Anyone who wants the original Kaggle benchmark can still
drop it into data/raw/ per the README's documented fallback path.
"""

import csv
import random
from pathlib import Path

import numpy as np

SEED = 42
N_STEPS = 744  # 31 simulated days x 24 hourly steps, matching PaySim's step semantics
N_CUSTOMERS = 10_000
N_MERCHANTS = 800
N_MULES = 40  # small pool of accounts fraud episodes launder funds through
N_FRAUD_EPISODES = 200  # TRANSFER-then-CASH_OUT drain pattern
N_STRUCTURING_EPISODES = 35  # sub-threshold splitting pattern
N_CIRCULAR_EPISODES = 15  # funds looping back to origin through several hops
AVG_TXNS_PER_STEP = 270  # ~200k rows total across 744 steps

STRUCTURING_BAND_LOW = 9_000
STRUCTURING_BAND_HIGH = 9_999

TXN_TYPE_WEIGHTS = {
    "CASH_OUT": 0.35,
    "PAYMENT": 0.34,
    "CASH_IN": 0.22,
    "TRANSFER": 0.08,
    "DEBIT": 0.01,
}
MERCHANT_DEST_TYPES = {"PAYMENT", "DEBIT"}  # PaySim quirk: merchant balances untracked (always 0/0)
FLAG_THRESHOLD = 200_000  # mirrors PaySim's own naive isFlaggedFraud rule

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "sample" / "paysim_sample.csv"


def make_accounts(rng: np.random.Generator) -> dict:
    customers = np.array([f"C{rng.integers(1_000_000_000, 1_999_999_999)}" for _ in range(N_CUSTOMERS)])
    merchants = np.array([f"M{rng.integers(1_000_000_000, 1_999_999_999)}" for _ in range(N_MERCHANTS)])
    mules = np.array([f"C{rng.integers(1_000_000_000, 1_999_999_999)}" for _ in range(N_MULES)])
    balances = {}
    for acct in customers:
        balances[acct] = float(rng.lognormal(mean=8.5, sigma=1.1))  # ~ hundreds to tens of thousands
    for acct in mules:
        balances[acct] = float(rng.lognormal(mean=6.0, sigma=0.8))  # mules start near-empty
    for acct in merchants:
        balances[acct] = 0.0  # merchant balances are never tracked in PaySim
    return {"customers": customers, "merchants": merchants, "mules": mules, "balances": balances}


def sample_txn_type(rng: np.random.Generator) -> str:
    types = list(TXN_TYPE_WEIGHTS.keys())
    weights = list(TXN_TYPE_WEIGHTS.values())
    return rng.choice(types, p=weights)


def sample_amount(rng: np.random.Generator, txn_type: str) -> float:
    scale = {"CASH_OUT": 6.5, "PAYMENT": 5.0, "CASH_IN": 6.3, "TRANSFER": 7.0, "DEBIT": 4.5}[txn_type]
    return float(round(rng.lognormal(mean=scale, sigma=1.3), 2))


def legit_transaction(rng: np.random.Generator, accounts: dict, step: int) -> dict | None:
    txn_type = sample_txn_type(rng)
    balances = accounts["balances"]
    orig = rng.choice(accounts["customers"])
    old_orig = balances[orig]
    amount = sample_amount(rng, txn_type)
    if amount > old_orig:
        amount = round(old_orig * rng.uniform(0.1, 0.9), 2)
    if amount <= 0:
        return None
    new_orig = round(old_orig - amount, 2)

    if txn_type in MERCHANT_DEST_TYPES:
        dest = rng.choice(accounts["merchants"])
        old_dest, new_dest = 0.0, 0.0
    else:
        dest = rng.choice(accounts["customers"])
        while dest == orig:
            dest = rng.choice(accounts["customers"])
        old_dest = balances[dest]
        new_dest = round(old_dest + amount, 2)

    balances[orig] = new_orig
    if dest in balances and txn_type not in MERCHANT_DEST_TYPES:
        balances[dest] = new_dest

    return {
        "step": step,
        "type": txn_type,
        "amount": amount,
        "nameOrig": orig,
        "oldbalanceOrg": round(old_orig, 2),
        "newbalanceOrig": new_orig,
        "nameDest": dest,
        "oldbalanceDest": round(old_dest, 2),
        "newbalanceDest": new_dest,
        "isFraud": 0,
        "isFlaggedFraud": 1 if (txn_type == "TRANSFER" and amount > FLAG_THRESHOLD) else 0,
    }


def fraud_episode(rng: np.random.Generator, accounts: dict, step: int) -> list[dict]:
    """TRANSFER-then-CASH_OUT drain pattern, with the destination-balance-zeroing
    label leakage that real PaySim exhibits (documented reason detection features
    must avoid raw balance columns — see docs/adr/0003)."""
    balances = accounts["balances"]
    victim = rng.choice(accounts["customers"])
    mule = rng.choice(accounts["mules"])
    old_victim = balances[victim]
    if old_victim < 1000:
        return []
    drain_amount = round(old_victim * rng.uniform(0.85, 1.0), 2)
    new_victim = 0.0

    rows = [
        {
            "step": step,
            "type": "TRANSFER",
            "amount": drain_amount,
            "nameOrig": victim,
            "oldbalanceOrg": round(old_victim, 2),
            "newbalanceOrig": new_victim,
            "nameDest": mule,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 0.0,  # unreported, matching PaySim's fraud-labeled quirk
            "isFraud": 1,
            "isFlaggedFraud": 1 if drain_amount > FLAG_THRESHOLD else 0,
        }
    ]
    balances[victim] = new_victim

    cashout_step = min(step + rng.integers(1, 3), N_STEPS - 1)
    cashout_dest = rng.choice(accounts["customers"])
    rows.append(
        {
            "step": cashout_step,
            "type": "CASH_OUT",
            "amount": drain_amount,
            "nameOrig": mule,
            "oldbalanceOrg": drain_amount,
            "newbalanceOrig": 0.0,
            "nameDest": cashout_dest,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 0.0,
            "isFraud": 1,
            "isFlaggedFraud": 0,
        }
    )
    return rows


def structuring_episode(rng: np.random.Generator, accounts: dict, step: int) -> list[dict]:
    """Several sub-threshold TRANSFERs from one account on the same day, splitting
    a larger sum to stay under a round reporting threshold -- classic smurfing."""
    balances = accounts["balances"]
    n_hops = int(rng.integers(3, 6))
    structurer = rng.choice(accounts["customers"])
    required = STRUCTURING_BAND_HIGH * n_hops
    if balances[structurer] < required:
        return []

    rows = []
    for hop in range(n_hops):
        amount = round(rng.uniform(STRUCTURING_BAND_LOW, STRUCTURING_BAND_HIGH), 2)
        dest = rng.choice(accounts["customers"])
        while dest == structurer:
            dest = rng.choice(accounts["customers"])
        old_orig = balances[structurer]
        new_orig = round(old_orig - amount, 2)
        old_dest = balances[dest]
        new_dest = round(old_dest + amount, 2)
        balances[structurer] = new_orig
        balances[dest] = new_dest
        rows.append(
            {
                "step": step,
                "type": "TRANSFER",
                "amount": amount,
                "nameOrig": structurer,
                "oldbalanceOrg": round(old_orig, 2),
                "newbalanceOrig": new_orig,
                "nameDest": dest,
                "oldbalanceDest": round(old_dest, 2),
                "newbalanceDest": new_dest,
                "isFraud": 1,
                "isFlaggedFraud": 0,
            }
        )
    return rows


def circular_flow_episode(rng: np.random.Generator, accounts: dict, step: int) -> list[dict]:
    """A short chain of TRANSFERs that loops back to its starting account within a
    few hours -- layering funds through intermediaries to obscure the trail."""
    balances = accounts["balances"]
    chain_length = int(rng.integers(3, 5))
    chain = rng.choice(accounts["customers"], size=chain_length, replace=False).tolist()
    origin_balance = balances[chain[0]]
    if origin_balance < 5_000:
        return []

    amount = round(origin_balance * rng.uniform(0.3, 0.6), 2)
    rows = []
    for hop in range(chain_length):
        sender = chain[hop]
        receiver = chain[(hop + 1) % chain_length]
        old_orig = balances[sender]
        hop_amount = min(amount, old_orig)
        if hop_amount <= 0:
            break
        new_orig = round(old_orig - hop_amount, 2)
        old_dest = balances[receiver]
        new_dest = round(old_dest + hop_amount, 2)
        balances[sender] = new_orig
        balances[receiver] = new_dest
        rows.append(
            {
                "step": min(step + hop, N_STEPS - 1),
                "type": "TRANSFER",
                "amount": hop_amount,
                "nameOrig": sender,
                "oldbalanceOrg": round(old_orig, 2),
                "newbalanceOrig": new_orig,
                "nameDest": receiver,
                "oldbalanceDest": round(old_dest, 2),
                "newbalanceDest": new_dest,
                "isFraud": 1,
                "isFlaggedFraud": 0,
            }
        )
        amount = hop_amount * 0.97  # small skim at each hop
    return rows


def main() -> None:
    rng = np.random.default_rng(SEED)
    random.seed(SEED)
    accounts = make_accounts(rng)

    all_episode_steps = rng.choice(
        range(N_STEPS - 5),
        size=N_FRAUD_EPISODES + N_STRUCTURING_EPISODES + N_CIRCULAR_EPISODES,
        replace=False,
    )
    drain_steps = set(all_episode_steps[:N_FRAUD_EPISODES].tolist())
    structuring_steps = set(
        all_episode_steps[N_FRAUD_EPISODES : N_FRAUD_EPISODES + N_STRUCTURING_EPISODES].tolist()
    )
    circular_steps = set(all_episode_steps[N_FRAUD_EPISODES + N_STRUCTURING_EPISODES :].tolist())

    rows: list[dict] = []
    for step in range(N_STEPS):
        n_txns = int(rng.poisson(AVG_TXNS_PER_STEP))
        for _ in range(n_txns):
            row = legit_transaction(rng, accounts, step)
            if row is not None:
                rows.append(row)
        if step in drain_steps:
            rows.extend(fraud_episode(rng, accounts, step))
        if step in structuring_steps:
            rows.extend(structuring_episode(rng, accounts, step))
        if step in circular_steps:
            rows.extend(circular_flow_episode(rng, accounts, step))

    rows.sort(key=lambda r: r["step"])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
        "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud", "isFlaggedFraud",
    ]
    with OUTPUT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    fraud_count = sum(r["isFraud"] for r in rows)
    print(f"Wrote {len(rows):,} rows to {OUTPUT_PATH}")
    print(f"Fraud rows: {fraud_count:,} ({fraud_count / len(rows):.3%})")
    print(f"Flagged-fraud rows: {sum(r['isFlaggedFraud'] for r in rows):,}")
    print(f"Step range: {rows[0]['step']}-{rows[-1]['step']}")


if __name__ == "__main__":
    main()
