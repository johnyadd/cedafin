/**
 * components/Spark.tsx — one chart, used everywhere a series is shown.
 *
 * WHY THIS IS A SHARED FILE
 * There were two copies: a 120×32 line on the shares page and a 220×64 filled
 * chart on the comparison pages. They drifted apart within a day, which meant
 * a Ghanaian share and a Treasury bill were drawn to different standards on
 * the same site for no reason a reader could see.
 *
 * WHY IT IS THIS SIZE AND NOT SMALLER
 * The first version was 96×26. At that size a line conveys that something
 * moved and nothing else — decoration, on a site whose whole argument is that
 * figures should mean something. Bigger, filled to the baseline, with the last
 * point marked: enough to read the shape at a glance.
 *
 * WHY THE CAPTION IS OPTIONAL
 * A line without a scale cannot distinguish a 2% move from a 200% one, so the
 * caption gives the start value, the change and the end value. But the shares
 * page already prints the percentage beside each chart, and showing it twice
 * is clutter. Off by default there, on everywhere else.
 *
 * WHY TEN POINTS MINIMUM
 * Platinum Debt Income Fund has six observations. A line through six readings
 * implies a trend the data cannot carry, and drawing nothing is the honest
 * outcome — the reader sees an absence rather than a shape that is mostly gaps.
 */

const COLOURS = {
  good: "#0E8F62",
  clay: "#C0492B",
  muted: "#5F726C",
};

export interface SparkProps {
  /** Oldest first. Fewer than `minPoints` draws nothing. */
  points: number[];
  /** "%" formats the caption as a rate; otherwise a plain number. */
  unit?: string;
  /** Start, change and end beneath the line. Off where the page shows them. */
  caption?: boolean;
  width?: number;
  height?: number;
  minPoints?: number;
}

export default function Spark({
  points,
  unit,
  caption = true,
  width = 220,
  height = 64,
  minPoints = 10,
}: SparkProps) {
  if (!points || points.length < minPoints) return null;

  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const pad = 4;
  const iw = width - pad * 2;
  const ih = height - pad * 2;

  const first = points[0];
  const last = points[points.length - 1];
  const up = last >= first;
  const colour = up ? COLOURS.good : COLOURS.clay;

  const xy = (p: number, i: number): [number, number] => [
    pad + (i / (points.length - 1)) * iw,
    pad + ih - ((p - min) / span) * ih,
  ];

  const line = points
    .map((p, i) => {
      const [x, y] = xy(p, i);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const area =
    `${line} L${(pad + iw).toFixed(1)},${(pad + ih).toFixed(1)} ` +
    `L${pad},${(pad + ih).toFixed(1)} Z`;

  const [lx, ly] = xy(last, points.length - 1);

  const fmt = (v: number) =>
    unit === "%"
      ? `${v.toFixed(2)}%`
      : v >= 1000
        ? v.toFixed(0)
        : v >= 100
          ? v.toFixed(1)
          : v.toFixed(2);

  const changePct = ((last - first) / (first || 1)) * 100;

  return (
    <div>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${fmt(first)} to ${fmt(last)}, ${changePct.toFixed(1)}%`}
      >
        <path d={area} fill={colour} opacity="0.08" />
        <path
          d={line}
          fill="none"
          stroke={colour}
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx={lx} cy={ly} r="2.75" fill={colour} />
      </svg>

      {caption && (
        <div
          className="mt-0.5 flex justify-between text-[10px] tabular-nums"
          style={{ color: COLOURS.muted }}
        >
          <span>{fmt(first)}</span>
          <span style={{ color: colour, fontWeight: 600 }}>
            {up ? "+" : ""}
            {changePct.toFixed(1)}%
          </span>
          <span>{fmt(last)}</span>
        </div>
      )}
    </div>
  );
}
