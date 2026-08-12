import pandas as pd

from detection.rules.structuring import detect


def _txn(key, orig, day, amount):
    return {"transaction_key": key, "origin_account_nk": orig, "day_offset": day, "amount": amount}


def test_flags_account_with_multiple_sub_threshold_transfers_same_day():
    txns = pd.DataFrame(
        [
            _txn("t1", "C1", 0, 9500),
            _txn("t2", "C1", 0, 9200),
            _txn("t3", "C1", 0, 9800),
        ]
    )
    result = detect(txns)
    assert set(result["transaction_key"]) == {"t1", "t2", "t3"}
    assert (result["rule_name"] == "structuring").all()


def test_does_not_flag_two_transactions_below_min_count():
    txns = pd.DataFrame([_txn("t1", "C1", 0, 9500), _txn("t2", "C1", 0, 9200)])
    result = detect(txns)
    assert result.empty


def test_does_not_flag_transactions_outside_band():
    txns = pd.DataFrame(
        [_txn("t1", "C1", 0, 5000), _txn("t2", "C1", 0, 6000), _txn("t3", "C1", 0, 7000)]
    )
    result = detect(txns)
    assert result.empty


def test_does_not_flag_transactions_spread_across_different_days():
    txns = pd.DataFrame(
        [_txn("t1", "C1", 0, 9500), _txn("t2", "C1", 1, 9200), _txn("t3", "C1", 2, 9800)]
    )
    result = detect(txns)
    assert result.empty


def test_ignores_other_accounts():
    txns = pd.DataFrame(
        [
            _txn("t1", "C1", 0, 9500),
            _txn("t2", "C1", 0, 9200),
            _txn("t3", "C1", 0, 9800),
            _txn("t4", "C2", 0, 9500),
        ]
    )
    result = detect(txns)
    assert "t4" not in set(result["transaction_key"])
