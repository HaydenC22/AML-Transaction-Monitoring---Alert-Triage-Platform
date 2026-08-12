import "./SeverityStamp.css";

type Severity = "low" | "medium" | "high" | "critical";

const LABELS: Record<Severity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export function SeverityStamp({ severity }: { severity: Severity }) {
  return (
    <span className={`severity-stamp severity-stamp-${severity}`}>
      {LABELS[severity]}
    </span>
  );
}
