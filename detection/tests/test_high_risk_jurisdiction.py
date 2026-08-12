import pandas as pd

from detection.rules.high_risk_jurisdiction import detect


def _txn(key, origin_high_risk, dest_high_risk):
    return {
        "transaction_key": key,
        "origin_is_high_risk": origin_high_risk,
        "dest_is_high_risk": dest_high_risk,
    }


def test_flags_high_risk_origin():
    txns = pd.DataFrame([_txn("t1", True, False)])
    result = detect(txns)
    assert set(result["transaction_key"]) == {"t1"}


def test_flags_high_risk_destination():
    txns = pd.DataFrame([_txn("t1", False, True)])
    result = detect(txns)
    assert set(result["transaction_key"]) == {"t1"}


def test_does_not_flag_when_neither_side_high_risk():
    txns = pd.DataFrame([_txn("t1", False, False)])
    result = detect(txns)
    assert result.empty


def test_handles_null_risk_flags_as_not_high_risk():
    txns = pd.DataFrame([_txn("t1", None, None)])
    result = detect(txns)
    assert result.empty
