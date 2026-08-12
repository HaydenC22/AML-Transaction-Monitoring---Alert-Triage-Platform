import { useMemo, useState } from "react";

import { niceScale } from "./niceScale";
import "./charts.css";

export interface LineSeries {
  name: string;
  color: string;
  points: { x: number; y: number }[];
}

const WIDTH = 560;
const HEIGHT = 220;
const MARGIN = { top: 16, right: 16, bottom: 28, left: 44 };

export function LineChart({
  series,
  xLabel,
  yFormat = (v: number) => v.toFixed(2),
  yDomain,
}: {
  series: LineSeries[];
  xLabel?: string;
  yFormat?: (value: number) => string;
  yDomain?: [number, number];
}) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const allPoints = series.flatMap((s) => s.points);
  const xs = allPoints.map((p) => p.x);
  const ys = allPoints.map((p) => p.y);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMin = yDomain ? yDomain[0] : 0;
  const rawYMax = yDomain ? yDomain[1] - yMin : Math.max(...ys, 0.0001);
  const { niceMax, ticks: niceTickOffsets } = niceScale(rawYMax, 4);
  const yMax = yMin + niceMax;

  const innerW = WIDTH - MARGIN.left - MARGIN.right;
  const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;

  const scaleX = (x: number) => (xMax === xMin ? 0 : ((x - xMin) / (xMax - xMin)) * innerW);
  const scaleY = (y: number) => innerH - ((y - yMin) / (yMax - yMin || 1)) * innerH;

  const paths = useMemo(
    () =>
      series.map((s) => {
        const d = s.points
          .map((p, i) => `${i === 0 ? "M" : "L"} ${scaleX(p.x).toFixed(2)} ${scaleY(p.y).toFixed(2)}`)
          .join(" ");
        return { name: s.name, color: s.color, d };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [series, xMin, xMax, yMin, yMax]
  );

  const tickValues = niceTickOffsets.map((t) => yMin + t);

  const referencePoints = series[0]?.points ?? [];

  return (
    <div className="chart-root">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={series.map((s) => s.name).join(", ")}
        onMouseLeave={() => setHoverIndex(null)}
      >
        <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
          {tickValues.map((t) => (
            <g key={t}>
              <line x1={0} x2={innerW} y1={scaleY(t)} y2={scaleY(t)} className="chart-gridline" />
              <text x={-8} y={scaleY(t)} className="chart-axis-label" textAnchor="end" dominantBaseline="middle">
                {yFormat(t)}
              </text>
            </g>
          ))}
          <line x1={0} x2={innerW} y1={innerH} y2={innerH} className="chart-baseline" />

          {paths.map((p) => (
            <path key={p.name} d={p.d} fill="none" stroke={p.color} strokeWidth={2} strokeLinecap="round" />
          ))}

          {hoverIndex !== null && referencePoints[hoverIndex] && (
            <line
              x1={scaleX(referencePoints[hoverIndex].x)}
              x2={scaleX(referencePoints[hoverIndex].x)}
              y1={0}
              y2={innerH}
              className="chart-crosshair"
            />
          )}

          {series.map((s) =>
            s.points.map((p, i) => (
              <circle
                key={`${s.name}-${i}`}
                cx={scaleX(p.x)}
                cy={scaleY(p.y)}
                r={hoverIndex === i ? 4 : 2.5}
                fill={s.color}
              />
            ))
          )}

          <rect
            x={0}
            y={0}
            width={innerW}
            height={innerH}
            fill="transparent"
            onMouseMove={(e) => {
              const rect = (e.target as SVGRectElement).getBoundingClientRect();
              const relX = e.clientX - rect.left;
              const ratio = relX / rect.width;
              const idx = Math.round(ratio * (referencePoints.length - 1));
              setHoverIndex(Math.min(Math.max(idx, 0), referencePoints.length - 1));
            }}
          />
        </g>
      </svg>
      {hoverIndex !== null && referencePoints[hoverIndex] && (
        <div className="chart-tooltip">
          <div className="chart-tooltip-x">
            {xLabel ?? "x"}: {referencePoints[hoverIndex].x}
          </div>
          {series.map((s) => (
            <div key={s.name} className="chart-tooltip-row">
              <span className="chart-tooltip-swatch" style={{ background: s.color }} />
              <span>{s.name}</span>
              <span className="mono chart-tooltip-value">
                {s.points[hoverIndex] ? yFormat(s.points[hoverIndex].y) : "–"}
              </span>
            </div>
          ))}
        </div>
      )}
      {series.length > 1 && (
        <div className="chart-legend">
          {series.map((s) => (
            <span key={s.name} className="chart-legend-item">
              <span className="chart-legend-swatch" style={{ background: s.color }} />
              {s.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
