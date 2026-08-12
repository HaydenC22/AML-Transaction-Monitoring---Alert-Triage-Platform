import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { BarChart } from "../charts/BarChart";
import { LineChart } from "../charts/LineChart";
import { Card } from "../components/Card";
import { PageHeader } from "../components/PageHeader";
import { StatTile } from "../components/StatTile";
import "./RulesTuningPage.css";

const RULE_COLORS: Record<string, string> = {
  structuring: "var(--cat-1)",
  velocity_spike: "var(--cat-2)",
  high_risk_jurisdiction: "var(--cat-3)",
  circular_flow: "var(--cat-4)",
};

export function RulesTuningPage() {
  const { data: curve } = useQuery({ queryKey: ["threshold-curve"], queryFn: api.getThresholdCurve });
  const { data: ruleVolume } = useQuery({ queryKey: ["rule-volume"], queryFn: api.getRuleVolume });
  const { data: recommendation } = useQuery({
    queryKey: ["threshold-recommendation"],
    queryFn: api.getThresholdRecommendation,
  });

  const chosenPoint = curve?.find((p) => p.threshold === recommendation?.current_threshold);

  return (
    <div>
      <PageHeader eyebrow="Detection calibration" title="Rules & Tuning" />

      <div className="threshold-callout">
        <StatTile label="Current operating threshold" value={recommendation?.current_threshold.toFixed(2) ?? "–"} />
        <StatTile
          label="Recommended threshold"
          value={recommendation?.recommended_threshold?.toFixed(2) ?? "Not yet available"}
          tone={recommendation?.recommended_threshold ? "good" : "neutral"}
          detail={
            recommendation
              ? `based on ${recommendation.dispositions_considered} analyst disposition${recommendation.dispositions_considered === 1 ? "" : "s"}`
              : undefined
          }
        />
        {chosenPoint && (
          <StatTile
            label="At current threshold"
            value={`${(chosenPoint.precision * 100).toFixed(1)}% precision`}
            detail={`${(chosenPoint.recall * 100).toFixed(1)}% recall · ${chosenPoint.alerts_flagged.toLocaleString()} alerts`}
          />
        )}
      </div>
      <p className="tuning-note">
        Recommendations are computed from analyst dispositions and never applied automatically — changing the
        operating threshold is a deliberate decision made by updating <code>CHOSEN_THRESHOLD</code> and
        redeploying the detection engine.
      </p>

      <div className="tuning-grid">
        <Card title="Precision vs. recall">
          {curve && curve.length > 0 ? (
            <LineChart
              series={[
                {
                  name: "Precision",
                  color: "var(--accent)",
                  points: [...curve]
                    .sort((a, b) => a.recall - b.recall)
                    .map((p) => ({ x: p.recall, y: p.precision })),
                },
              ]}
              xLabel="recall"
              yFormat={(v) => `${(v * 100).toFixed(0)}%`}
              yDomain={[0, 1]}
            />
          ) : (
            <p className="muted-text">No alerts to evaluate yet.</p>
          )}
        </Card>

        <Card title="Recall & false-positive rate by threshold">
          {curve && curve.length > 0 ? (
            <LineChart
              series={[
                {
                  name: "Recall",
                  color: "var(--accent)",
                  points: curve.map((p) => ({ x: p.threshold, y: p.recall })),
                },
                {
                  name: "FP rate",
                  color: "var(--status-high)",
                  points: curve.map((p) => ({ x: p.threshold, y: p.fp_rate })),
                },
              ]}
              xLabel="threshold"
              yFormat={(v) => `${(v * 100).toFixed(1)}%`}
            />
          ) : (
            <p className="muted-text">No alerts to evaluate yet.</p>
          )}
        </Card>
      </div>

      <Card title="Alert volume by rule">
        {ruleVolume && ruleVolume.length > 0 ? (
          <BarChart
            data={ruleVolume.map((r) => ({
              label: r.rule_name.replace(/_/g, " "),
              value: r.alert_count,
              color: RULE_COLORS[r.rule_name] ?? "var(--accent)",
            }))}
          />
        ) : (
          <p className="muted-text">No rule-triggered alerts yet.</p>
        )}
      </Card>
    </div>
  );
}
