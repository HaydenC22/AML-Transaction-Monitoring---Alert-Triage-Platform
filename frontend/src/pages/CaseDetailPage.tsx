import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import { LineChart } from "../charts/LineChart";
import { Card } from "../components/Card";
import { PageHeader } from "../components/PageHeader";
import { SeverityStamp } from "../components/SeverityStamp";
import "./CaseDetailPage.css";

const RULE_EXPLANATIONS: Record<string, string> = {
  structuring: "Several transfers just under a round reporting threshold, aggregating to a large sum.",
  velocity_spike: "Outgoing activity on this day is a large multiple of the account's own trailing baseline.",
  high_risk_jurisdiction: "The origin or destination account resolves to a high-risk synthetic jurisdiction.",
  circular_flow: "Funds traced through a short cycle of transfers that loops back to the origin.",
};

export function CaseDetailPage() {
  const { alertId } = useParams<{ alertId: string }>();
  const id = Number(alertId);
  const queryClient = useQueryClient();

  const { data: alert, isLoading, isError } = useQuery({
    queryKey: ["alert", id],
    queryFn: () => api.getAlert(id),
    enabled: Number.isFinite(id),
  });
  const { data: timeline } = useQuery({
    queryKey: ["case-timeline", id],
    queryFn: () => api.getCaseTimeline(id),
    enabled: Number.isFinite(id),
  });

  const [analystId, setAnalystId] = useState("");
  const [outcome, setOutcome] = useState<"true_positive" | "false_positive">("false_positive");
  const [rationale, setRationale] = useState("");
  const [noteText, setNoteText] = useState("");
  const [noteAuthor, setNoteAuthor] = useState("");

  const dispositionMutation = useMutation({
    mutationFn: () => api.dispositionAlert(id, { analyst_id: analystId, outcome, rationale_notes: rationale }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert", id] });
      setRationale("");
    },
  });

  const noteMutation = useMutation({
    mutationFn: () => api.addNote(id, { author: noteAuthor, note_text: noteText }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert", id] });
      setNoteText("");
    },
  });

  if (isLoading) return <p className="page-status">Loading case…</p>;
  if (isError || !alert) return <p className="page-status page-status-error">Case not found.</p>;

  return (
    <div>
      <Link to="/alerts" className="back-link">
        ← Back to queue
      </Link>
      <PageHeader
        eyebrow={`Case #${alert.alert_id} · ${alert.transaction_key.slice(0, 12)}…`}
        title={`${alert.origin_account_nk} — ${alert.transaction_type}`}
        action={<SeverityStamp severity={alert.severity} />}
      />

      <div className="case-grid">
        <div className="case-main">
          <Card title="Transaction context">
            <dl className="detail-list">
              <div>
                <dt>Amount</dt>
                <dd className="mono">${alert.amount.toLocaleString()}</dd>
              </div>
              <div>
                <dt>Composite score</dt>
                <dd className="mono">{alert.composite_score.toFixed(2)}</dd>
              </div>
              <div>
                <dt>ML anomaly score</dt>
                <dd className="mono">{alert.ml_anomaly_score.toFixed(2)}</dd>
              </div>
              <div>
                <dt>Origin geography</dt>
                <dd className="mono">{alert.origin_geography_key?.slice(0, 8) ?? "—"}</dd>
              </div>
              <div>
                <dt>Destination geography</dt>
                <dd className="mono">{alert.dest_geography_key?.slice(0, 8) ?? "—"}</dd>
              </div>
              <div>
                <dt>Recorded fraud label</dt>
                <dd>{alert.is_fraud_label ? "Yes (synthetic ground truth)" : "No"}</dd>
              </div>
            </dl>
          </Card>

          <Card title="Triggered rules">
            {alert.rule_flags.length === 0 ? (
              <p className="muted-text">
                No deterministic rule fired for this alert — it was surfaced by the Isolation Forest anomaly
                score alone.
              </p>
            ) : (
              <ul className="rule-list">
                {alert.rule_flags.map((r) => (
                  <li key={r}>
                    <span className="rule-list-name">{r.replace(/_/g, " ")}</span>
                    <span className="rule-list-explanation">{RULE_EXPLANATIONS[r]}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Account activity (transactions per simulated day)">
            {timeline && timeline.length > 0 ? (
              <LineChart
                series={[
                  {
                    name: "Transactions",
                    color: "var(--accent)",
                    points: timeline.map((t) => ({ x: t.day_offset, y: t.transaction_count })),
                  },
                ]}
                xLabel="day"
                yFormat={(v) => v.toFixed(0)}
              />
            ) : (
              <p className="muted-text">No account history available.</p>
            )}
          </Card>
        </div>

        <div className="case-side">
          <Card title="Disposition">
            {alert.disposition ? (
              <div className="disposition-summary">
                <span className={`status-pill status-pill-${alert.disposition.outcome === "true_positive" ? "closed" : "open"}`}>
                  {alert.disposition.outcome.replace("_", " ")}
                </span>
                <p className="muted-text">{alert.disposition.rationale_notes}</p>
                <p className="muted-text">
                  — {alert.disposition.analyst_id}, {new Date(alert.disposition.dispositioned_at).toLocaleString()}
                </p>
              </div>
            ) : (
              <form
                className="disposition-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  dispositionMutation.mutate();
                }}
              >
                <label>
                  Analyst ID
                  <input value={analystId} onChange={(e) => setAnalystId(e.target.value)} required />
                </label>
                <fieldset>
                  <label className="radio-row">
                    <input
                      type="radio"
                      name="outcome"
                      checked={outcome === "false_positive"}
                      onChange={() => setOutcome("false_positive")}
                    />
                    False positive
                  </label>
                  <label className="radio-row">
                    <input
                      type="radio"
                      name="outcome"
                      checked={outcome === "true_positive"}
                      onChange={() => setOutcome("true_positive")}
                    />
                    True positive
                  </label>
                </fieldset>
                <label>
                  Rationale
                  <textarea
                    value={rationale}
                    onChange={(e) => setRationale(e.target.value)}
                    required
                    rows={4}
                  />
                </label>
                <button type="submit" disabled={dispositionMutation.isPending}>
                  {dispositionMutation.isPending ? "Submitting…" : "Submit disposition"}
                </button>
                {dispositionMutation.isError && (
                  <p className="form-error">Couldn't submit — this alert may already be dispositioned.</p>
                )}
              </form>
            )}
          </Card>

          <Card title="Case notes">
            <ul className="notes-list">
              {alert.notes.map((n) => (
                <li key={n.note_id}>
                  <p>{n.note_text}</p>
                  <span className="muted-text">
                    {n.author} · {new Date(n.created_at).toLocaleString()}
                  </span>
                </li>
              ))}
              {alert.notes.length === 0 && <p className="muted-text">No notes yet.</p>}
            </ul>
            <form
              className="note-form"
              onSubmit={(e) => {
                e.preventDefault();
                noteMutation.mutate();
              }}
            >
              <input placeholder="Your name" value={noteAuthor} onChange={(e) => setNoteAuthor(e.target.value)} required />
              <textarea
                placeholder="Add a note…"
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                required
                rows={2}
              />
              <button type="submit" disabled={noteMutation.isPending}>
                Add note
              </button>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
