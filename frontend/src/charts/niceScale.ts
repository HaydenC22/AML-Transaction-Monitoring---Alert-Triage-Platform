function niceNumber(range: number, round: boolean): number {
  if (range === 0) return 1;
  const exponent = Math.floor(Math.log10(range));
  const fraction = range / 10 ** exponent;
  let niceFraction: number;

  if (round) {
    if (fraction < 1.5) niceFraction = 1;
    else if (fraction < 3) niceFraction = 2;
    else if (fraction < 7) niceFraction = 5;
    else niceFraction = 10;
  } else {
    if (fraction <= 1) niceFraction = 1;
    else if (fraction <= 2) niceFraction = 2;
    else if (fraction <= 5) niceFraction = 5;
    else niceFraction = 10;
  }
  return niceFraction * 10 ** exponent;
}

/** Rounds [0, maxValue] to a "nice" axis range with evenly-spaced ticks,
 * avoiding floating-point-ridden tick labels like 13633.249999999998. */
export function niceScale(maxValue: number, tickCount = 4): { niceMax: number; ticks: number[] } {
  if (maxValue <= 0) return { niceMax: 1, ticks: [0, 1] };
  const step = niceNumber(maxValue / tickCount, true);
  const niceMax = Math.ceil(maxValue / step) * step;
  const ticks: number[] = [];
  for (let t = 0; t <= niceMax + step / 2; t += step) {
    ticks.push(Math.round(t * 1e6) / 1e6);
  }
  return { niceMax, ticks };
}
