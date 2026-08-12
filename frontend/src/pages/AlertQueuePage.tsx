import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api, type AlertSummary } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { SeverityStamp } from "../components/SeverityStamp";
import "./AlertQueuePage.css";

const RULES = ["structuring", "velocity_spike", "high_risk_jurisdiction", "circular_flow"];
const PAGE_SIZE = 25;

type SortKey = "composite_score" | "amount" | "created_at";

export function AlertQueuePage() {
  const [status, setStatus] = useState<"" | "open" | "closed">("");
  const [severity, setSeverity] = useState<"" | AlertSummary["severity"]>("");
  const [rule, setRule] = useState("");
  const [page, setPage] = useState(1);
  const [sortKey, setSortKey] = useState<SortKey>("composite_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["alerts", { status, severity, rule, page }],
    queryFn: () =>
      api.listAlerts({
        status: status || undefined,
        severity: severity || undefined,
        rule: rule || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
  });

  const sortedItems = useMemo(() => {
    const items = data?.items ?? [];
    const sorted = [...items].sort((a, b) => {
      const diff =
        sortKey === "created_at"
          ? new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          : a[sortKey] - b[sortKey];
      return sortDir === "asc" ? diff : -diff;
    });
    return sorted;
  }, [data, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  function resetToFirstPage<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v);
      setPage(1);
    };
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <PageHeader eyebrow={data ? `${data.total.toLocaleString()} alerts` : undefined} title="Alert Queue" />

      <div className="filter-bar" role="group" aria-label="Filter alerts">
        <label>
          Status
          <select value={status} onChange={(e) => resetToFirstPage(setStatus)(e.target.value as typeof status)}>
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>
        </label>
        <label>
          Severity
          <select value={severity} onChange={(e) => resetToFirstPage(setSeverity)(e.target.value as typeof severity)}>
            <option value="">All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
        <label>
          Rule
          <select value={rule} onChange={(e) => resetToFirstPage(setRule)(e.target.value)}>
            <option value="">All</option>
            {RULES.map((r) => (
              <option key={r} value={r}>
                {r.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </label>
      </div>

      {isLoading && <p className="page-status">Loading alerts…</p>}
      {isError && <p className="page-status page-status-error">Couldn't load alerts. Is the API running?</p>}

      {data && (
        <>
          <div className="table-wrap">
            <table className="alert-table">
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>
                    <button className="th-sort" onClick={() => toggleSort("amount")}>
                      Amount {sortKey === "amount" ? (sortDir === "asc" ? "↑" : "↓") : ""}
                    </button>
                  </th>
                  <th>Type</th>
                  <th>Account</th>
                  <th>Rules triggered</th>
                  <th>
                    <button className="th-sort" onClick={() => toggleSort("composite_score")}>
                      Score {sortKey === "composite_score" ? (sortDir === "asc" ? "↑" : "↓") : ""}
                    </button>
                  </th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {sortedItems.map((alert) => (
                  <tr key={alert.alert_id}>
                    <td>
                      <SeverityStamp severity={alert.severity} />
                    </td>
                    <td className="mono">${alert.amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                    <td>{alert.transaction_type}</td>
                    <td className="mono">
                      <Link to={`/alerts/${alert.alert_id}`}>{alert.origin_account_nk}</Link>
                    </td>
                    <td className="rules-cell">
                      {alert.rule_flags.length > 0
                        ? alert.rule_flags.map((r) => (
                            <span key={r} className="rule-chip">
                              {r.replace(/_/g, " ")}
                            </span>
                          ))
                        : <span className="rule-chip rule-chip-ml">ML only</span>}
                    </td>
                    <td className="mono">{alert.composite_score.toFixed(2)}</td>
                    <td>
                      <span className={`status-pill status-pill-${alert.status}`}>{alert.status}</span>
                    </td>
                  </tr>
                ))}
                {sortedItems.length === 0 && (
                  <tr>
                    <td colSpan={7} className="empty-row">
                      No alerts match these filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <span className="mono">
              Page {page} of {totalPages}
            </span>
            <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
