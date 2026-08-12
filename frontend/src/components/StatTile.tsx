import "./StatTile.css";

export function StatTile({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: string;
  detail?: string;
  tone?: "neutral" | "good" | "warning";
}) {
  return (
    <div className="stat-tile">
      <span className="stat-tile-label">{label}</span>
      <span className={`stat-tile-value mono stat-tile-value-${tone}`}>{value}</span>
      {detail && <span className="stat-tile-detail">{detail}</span>}
    </div>
  );
}
