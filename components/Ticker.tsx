/**
 * components/Ticker.tsx — live levels, each with a readable shape.
 *
 * WHY THE SPARKLINES GREW
 * The first version drew them at 46×14. At that size a line is a scribble: it
 * shows that something moved and nothing about how. A ticker figure without
 * its shape is just a number, and the whole reason for putting a chart there
 * was that "91-day bill 5.08%" hides the rate having been 5.87% in July.
 *
 * 78×26 with the area filled underneath is enough to read at a glance, and
 * costs about twelve pixels of row height.
 *
 * WHY IT SCROLLS AND NOTHING ELSE DOES
 * A ticker is a line of short glanceable figures; miss one and it comes round
 * again. That is how every exchange presents live levels. Charts, tables and
 * articles are different, and this is deliberately the only moving element on
 * the site.
 *
 * WHY IT PAUSES
 * On hover, so a reader can finish looking. And entirely for anyone whose
 * system asks for reduced motion — a moving strip is a real problem for some
 * vestibular conditions and honouring that costs one media query.
 *
 * WHY EVERY ITEM CARRIES ITS DATE
 * A ticker implies "now". The GSE index comes from a monthly report that may
 * be six weeks old, the bill rate from the last tender. Presenting either as
 * today's would be the unstated staleness this site criticises elsewhere.
 */

const C = {
  gold: "#E8A33D",
  rule: "#1E3A4A",
  muted: "#9DB4C2",
  up: "#5FD3A0",
  down: "#F08A72",
};

export interface TickerItem {
  label: string;
  value: string;
  direction?: "up" | "down";
  asOf?: string;
  /** Recent observations, oldest first. Fewer than three draws nothing. */
  series?: number[];
}

function Spark({ points, colour }: { points: number[]; colour: string }) {
  if (!points || points.length < 3) return null;

  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const w = 78;
  const h = 26;
  const pad = 2;
  const iw = w - pad * 2;
  const ih = h - pad * 2;

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

  // Filled to the baseline so the shape reads as a quantity rather than a
  // squiggle — the difference between a chart and a scribble at this size.
  const area =
    `${line} L${(pad + iw).toFixed(1)},${(pad + ih).toFixed(1)} ` +
    `L${pad},${(pad + ih).toFixed(1)} Z`;

  const [lx, ly] = xy(points[points.length - 1], points.length - 1);

  return (
    <svg
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      aria-hidden="true"
      className="shrink-0"
    >
      <path d={area} fill={colour} opacity="0.15" />
      <path
        d={line}
        fill="none"
        stroke={colour}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={lx} cy={ly} r="2" fill={colour} />
    </svg>
  );
}

function Item({ it }: { it: TickerItem }) {
  const colour =
    it.direction === "up" ? C.up : it.direction === "down" ? C.down : C.gold;
  return (
    <div className="flex shrink-0 items-center gap-2.5 px-6 text-[12px]">
      <div className="flex flex-col">
        <span
          className="font-semibold uppercase tracking-wider"
          style={{ color: C.muted, fontSize: "9.5px" }}
        >
          {it.label}
        </span>
        <span className="flex items-baseline gap-1.5">
          <span
            className="font-bold tabular-nums"
            style={{ color: colour, fontSize: "13px" }}
          >
            {it.value}
          </span>
          {it.asOf && (
            <span style={{ color: C.muted, fontSize: "9.5px" }}>{it.asOf}</span>
          )}
        </span>
      </div>
      <Spark points={it.series ?? []} colour={colour} />
    </div>
  );
}

export default function Ticker({ items }: { items: TickerItem[] }) {
  if (!items.length) return null;

  // Rendered twice and translated by exactly half the track width, so the
  // second copy arrives as the first leaves. One copy would snap back visibly
  // at the end of every pass.
  return (
    <div
      className="w-full overflow-hidden"
      style={{ background: "#0B2733", borderBottom: `1px solid ${C.rule}` }}
    >
      <style>{`
        @keyframes cedafin-ticker {
          from { transform: translateX(0); }
          to   { transform: translateX(-50%); }
        }
        .cedafin-ticker-track {
          display: flex;
          width: max-content;
          animation: cedafin-ticker 52s linear infinite;
        }
        .cedafin-ticker-strip:hover .cedafin-ticker-track {
          animation-play-state: paused;
        }
        /* Was #1E3A4A on a #0B2733 background — technically present and
           invisible. Lightened so the items actually read as separate. */
        .cedafin-ticker-item + .cedafin-ticker-item {
          border-left: 1px solid #5A7D91;
        }
        @media (prefers-reduced-motion: reduce) {
          .cedafin-ticker-track { animation: none; }
        }
      `}</style>

      <div className="cedafin-ticker-strip py-2">
        <div className="cedafin-ticker-track">
          {[...items, ...items].map((it, i) => (
            <div key={`${it.label}-${i}`} className="cedafin-ticker-item">
              <Item it={it} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
