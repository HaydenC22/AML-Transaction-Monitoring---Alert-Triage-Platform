"""Circular fund flow rule: flags TRANSFER transactions that participate in a
short cycle (2-5 hops) in the account transfer graph within a rolling 3-day
window -- funds substantially returning to their origin, a classic layering
pattern. Restricted to TRANSFER type (the type PaySim uses for account-to-account
movement) to keep the graph sparse enough for exact cycle enumeration."""

import networkx as nx
import pandas as pd

RULE_NAME = "circular_flow"
WINDOW_DAYS = 3
MAX_CYCLE_LENGTH = 5
MAX_CYCLES_PER_WINDOW = 5_000  # guard against pathological dense windows


def detect(transactions: pd.DataFrame) -> pd.DataFrame:
    transfers = transactions[transactions["transaction_type"] == "TRANSFER"]
    if transfers.empty:
        return _empty_result()

    flagged_keys: set[str] = set()
    max_day = int(transactions["day_offset"].max())

    for window_start in range(0, max_day + 1, WINDOW_DAYS):
        window_end = window_start + WINDOW_DAYS - 1
        window_txns = transfers[
            (transfers["day_offset"] >= window_start) & (transfers["day_offset"] <= window_end)
        ]
        if window_txns.empty:
            continue

        graph = nx.MultiDiGraph()
        for row in window_txns.itertuples(index=False):
            graph.add_edge(row.origin_account_nk, row.dest_account_nk, transaction_key=row.transaction_key)

        simple_graph = nx.DiGraph(graph)  # collapse parallel edges for cycle search
        cycle_count = 0
        for cycle in nx.simple_cycles(simple_graph, length_bound=MAX_CYCLE_LENGTH):
            cycle_count += 1
            if cycle_count > MAX_CYCLES_PER_WINDOW:
                break
            nodes_in_cycle = set(cycle)
            edge_pairs = list(zip(cycle, cycle[1:] + cycle[:1]))
            for u, v in edge_pairs:
                if graph.has_edge(u, v):
                    for _, edge_data in graph.get_edge_data(u, v).items():
                        flagged_keys.add(edge_data["transaction_key"])

    if not flagged_keys:
        return _empty_result()

    result = pd.DataFrame({"transaction_key": sorted(flagged_keys)})
    result["rule_name"] = RULE_NAME
    return result


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=["transaction_key", "rule_name"])
