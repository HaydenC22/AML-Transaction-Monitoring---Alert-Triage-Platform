import pandas as pd

from detection.rules.circular_flow import detect


def _transfer(key, orig, dest, day):
    return {
        "transaction_key": key,
        "origin_account_nk": orig,
        "dest_account_nk": dest,
        "day_offset": day,
        "transaction_type": "TRANSFER",
    }


def test_flags_three_hop_cycle_back_to_origin():
    txns = pd.DataFrame(
        [
            _transfer("t1", "A", "B", 0),
            _transfer("t2", "B", "C", 0),
            _transfer("t3", "C", "A", 1),
        ]
    )
    result = detect(txns)
    assert set(result["transaction_key"]) == {"t1", "t2", "t3"}


def test_does_not_flag_linear_chain_without_cycle():
    txns = pd.DataFrame(
        [
            _transfer("t1", "A", "B", 0),
            _transfer("t2", "B", "C", 0),
            _transfer("t3", "C", "D", 1),
        ]
    )
    result = detect(txns)
    assert result.empty


def test_ignores_non_transfer_types():
    txns = pd.DataFrame(
        [
            {**_transfer("t1", "A", "B", 0), "transaction_type": "PAYMENT"},
            {**_transfer("t2", "B", "A", 0), "transaction_type": "PAYMENT"},
        ]
    )
    result = detect(txns)
    assert result.empty


def test_does_not_flag_cycle_split_across_distant_windows():
    txns = pd.DataFrame(
        [
            _transfer("t1", "A", "B", 0),
            _transfer("t2", "B", "C", 0),
            _transfer("t3", "C", "A", 20),  # far outside the 3-day rolling window
        ]
    )
    result = detect(txns)
    assert result.empty
