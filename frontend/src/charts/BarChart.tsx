import { niceScale } from "./niceScale";
import "./charts.css";

export interface BarDatum {
  label: string;
  value: number;
  color: string;
}

const WIDTH = 560;
const HEIGHT = 220;
const MARGIN = { top: 16, right: 16, bottom: 36, left: 56 };

export function BarChart({
  data,
  yFormat = (v: number) => Math.round(v).toLocaleString(),
}: {
  data: BarDatum[];
  yFormat?: (value: number) => string;
}) {
  const innerW = WIDTH - MARGIN.left - MARGIN.right;
  const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;
  const rawMax = Math.max(...data.map((d) => d.value), 1);
  const { niceMax, ticks } = niceScale(rawMax, 4);
  const maxValue = niceMax;

  const bandWidth = innerW / data.length;
  const barWidth = Math.min(bandWidth * 0.55, 56);

  return (
    <div className="chart-root">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Bar chart">
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={0} x2={innerW} y1={innerH - (t / maxValue) * innerH} y2={innerH - (t / maxValue) * innerH} className="chart-gridline" />
              <text
                x={-8}
                y={innerH - (t / maxValue) * innerH}
                className="chart-axis-label"
                textAnchor="end"
                dominantBaseline="middle"
              >
                {yFormat(t)}
              </text>
            </g>
          ))}
          <line x1={0} x2={innerW} y1={innerH} y2={innerH} className="chart-baseline" />

          {data.map((d, i) => {
            const barHeight = (d.value / maxValue) * innerH;
            const x = i * bandWidth + (bandWidth - barWidth) / 2;
            const y = innerH - barHeight;
            return (
              <g key={d.label}>
                <rect x={x} y={y} width={barWidth} height={Math.max(barHeight, 0)} rx={3} fill={d.color}>
                  <title>
                    {d.label}: {yFormat(d.value)}
                  </title>
                </rect>
                <text x={i * bandWidth + bandWidth / 2} y={innerH + 16} textAnchor="middle" className="chart-axis-label">
                  {d.label}
                </text>
                <text
                  x={i * bandWidth + bandWidth / 2}
                  y={y - 6}
                  textAnchor="middle"
                  className="chart-bar-value mono"
                >
                  {yFormat(d.value)}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
