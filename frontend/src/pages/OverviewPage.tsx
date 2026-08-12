import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { BarChart } from "../charts/BarChart";
import { LineChart } from "../charts/LineChart";
import { Card } from "../components/Card";
import { PageHeader } from "../components/PageHeader";
import { StatTile } from "../components/StatTile";
import "./OverviewPage.css";

const SEVERITY_COLOR: Record<string, string> = {
  low: "var(--status-low)",
  medium: "var(--status-medium)",
  high: "var(--status-high)",
  critical: "var(--status-critical)",
};

export function OverviewPage() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["overview"], queryFn: api.getOverview });

  if (isLoading) return <p className="page-status">Loading overview…</p>;
  if (isError || !data) return <p className="page-status page-status-error">Couldn't load pipeline metrics. Is the API running?</p>;

  const run = data.latest_pipeline_run;
  const totalAlerts = data.severity_breakdown.reduce((sum, s) => sum + s.alert_count, 0);
  const totalTruePositives = data.severity_breakdown.reduce((sum, s) => sum + s.true_positive_count, 0);
  const overallPrecision = totalAlerts ? (totalTruePositives / totalAlerts) * 100 : 0;
  const latestFpRow = data.fp_rate_trend.at(-1);
  const totalDispositions = data.analyst_throughput_by_day.reduce((sum, d) => sum + d.dispositions, 0);

  return (
    <div>
      <PageHeader eyebrow="Pipeline & alert health" title="Overview" />

      <Card>
        <div className="health-strip">
          <span className={`health-badge ${run?.ge_status === "passed" ? "health-badge-good" : "health-badge-bad"}`}>
            {run ? (run.ge_status === "passed" ? "Last run passed" : "Last run failed") : "No pipeline run yet"}
          </span>
          {run && (
            <>
              <span className="health-item mono">{run.rows_processed.toLocaleString()} rows processed</span>
              <span className="health-item mono">{run.alerts_generated.toLocaleString()} alerts generated</span>
              <span className="health-item mono">{run.runtime_seconds.toFixed(2)}s runtime</span>
              <span className="health-item mono">run #{run.run_id}</span>
            </>
          )}
        </div>
      </Card>

      <div className="stat-grid">
        <StatTile label="Total alerts" value={totalAlerts.toLocaleString()} />
        <StatTile
          label="Overall precision"
          value={`${overallPrecision.toFixed(1)}%`}
          detail="of all alerts are true fraud"
        />
        <StatTile
          label="Critical-tier precision"
          value={`${(
            (100 *
              (data.severity_breakdown.find((s) => s.severity === "critical")?.true_positive_count ?? 0)) /
            (data.severity_breakdown.find((s) => s.severity === "critical")?.alert_count || 1)
          ).toFixed(1)}%`}
          tone="good"
          detail="precision jumps at the top tier"
        />
        <StatTile
          label="Dispositions logged"
          value={totalDispositions.toLocaleString()}
          detail={latestFpRow ? `${latestFpRow.fp_rate_pct}% FP rate, most recent day` : "No dispositions yet"}
        />
      </div>

      <div className="overview-grid">
        <Card title="Alert volume by simulated day">
          <BarChart
            data={data.alert_volume_by_day.slice(-14).map((d) => ({
              label: String(d.day_offset),
              value: d.alert_count,
              color: "var(--accent)",
            }))}
          />
        </Card>
        <Card title="Alerts by severity">
          <BarChart
            data={["low", "medium", "high", "critical"].map((severity) => {
              const row = data.severity_breakdown.find((s) => s.severity === severity);
              return { label: severity, value: row?.alert_count ?? 0, color: SEVERITY_COLOR[severity] };
            })}
          />
        </Card>
      </div>

      {data.fp_rate_trend.length > 1 && (
        <Card title="False-positive rate trend (by disposition day)">
          <LineChart
            series={[
              {
                name: "FP rate",
                color: "var(--status-high)",
                points: data.fp_rate_trend.map((d, i) => ({ x: i, y: d.fp_rate_pct })),
              },
            ]}
            yFormat={(v) => `${v.toFixed(0)}%`}
          />
        </Card>
      )}
    </div>
  );
}
