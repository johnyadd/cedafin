/**
 * components/Ticker.tsx — the live numbers, across the top.
 *
 * WHY THIS IS THE STRONGEST THING ON THE PAGE
 * Every figure in it comes from a document its issuer published, and no other
 * Ghanaian site carries them together: Treasury bill rates from Bank of
 * Ghana's tender results, the Ghana Gold Coin from BoG's daily circulars, the
 * GSE Composite Index from the exchange's monthly reports, the cheapest fund
 * charge from the factsheets.
 *
 * A visitor who lands here and sees five current Ghanaian numbers learns in
 * two seconds what the site is, without reading a word of explanation.
 *
 * WHY EVERY FIGURE CARRIES A DATE
 * A ticker implies "now". The Treasury bill rate is from the most recent
 * tender, the index from the last monthly report — which may be six weeks old.
 * Presenting a July index figure as though it were today's would be exactly
 * the sort of unstated staleness this site criticises elsewhere, so each item
 * says when it was true.
 *
 * WHAT IT DELIBERATELY DOES NOT DO
 * Scroll or animate. A moving ticker is harder to read and implies real-time
 * data that monthly reports cannot support.
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
  /** "up" | "down" | undefined — direction since the previous reading. */
  direction?: "up" | "down";
  /** When this figure was true. A ticker implies now; most of these are not. */
  asOf?: string;
}

export default function Ticker({ items }: { items: TickerItem[] }) {
  if (!items.length) return null;

  return (
    <div
      className="w-full overflow-x-auto"
      style={{ background: "#0B2733", borderBottom: `1px solid ${C.rule}` }}
    >
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-5 py-2.5 sm:px-8">
        {items.map((it, i) => (
          <div
            key={it.label}
            className="flex shrink-0 items-baseline gap-2 text-[12px]"
            style={{
              paddingRight: i < items.length - 1 ? "1.5rem" : 0,
              borderRight:
                i < items.length - 1 ? `1px solid ${C.rule}` : "none",
            }}
          >
            <span
              className="font-semibold uppercase tracking-wider"
              style={{ color: C.muted, fontSize: "10.5px" }}
            >
              {it.label}
            </span>
            <span
              className="font-bold tabular-nums"
              style={{
                color:
                  it.direction === "up"
                    ? C.up
                    : it.direction === "down"
                      ? C.down
                      : C.gold,
              }}
            >
              {it.value}
            </span>
            {it.asOf && (
              <span style={{ color: C.muted, fontSize: "10px" }}>
                {it.asOf}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
