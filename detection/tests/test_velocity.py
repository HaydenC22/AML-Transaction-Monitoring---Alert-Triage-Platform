import pandas as pd

from detection.rules.velocity import detect


def _txn(key, orig, day, amount):
    return {"transaction_key": key, "origin_account_nk": orig, "day_offset": day, "amount": amount}


def _steady_history(orig, days, daily_amount):
    return [_txn(f"{orig}-hist-{d}", orig, d, daily_amount) for d in days]


def test_flags_day_with_large_multiple_of_baseline():
    history = _steady_history("C1", range(6), 1000)
    spike = [_txn("spike", "C1", 6, 20000)]  # far above 5x the 1000 baseline
    txns = pd.DataFrame(history + spike)
    result = detect(txns)
    assert "spike" in set(result["transaction_key"])


def test_does_not_flag_without_enough_baseline_history():
    history = _steady_history("C1", range(2), 1000)  # only 2 prior days, below MIN_BASELINE_DAYS
    spike = [_txn("spike", "C1", 2, 20000)]
    txns = pd.DataFrame(history + spike)
    result = detect(txns)
    assert result.empty


def test_does_not_flag_mild_increase():
    history = _steady_history("C1", range(6), 1000)
    mild = [_txn("mild", "C1", 6, 1500)]  # 1.5x baseline, below SPIKE_MULTIPLIER
    txns = pd.DataFrame(history + mild)
    result = detect(txns)
    assert result.empty


def test_does_not_flag_trivial_amounts_below_floor():
    history = _steady_history("C1", range(6), 10)
    spike = [_txn("spike", "C1", 6, 100)]  # 10x baseline but tiny absolute amount
    txns = pd.DataFrame(history + spike)
    result = detect(txns)
    assert result.empty
