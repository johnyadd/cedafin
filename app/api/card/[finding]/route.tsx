import { ImageResponse } from "next/og";

/**
 * app/api/card/[finding]/route.tsx — a finding as an image.
 *
 * WHY IMAGES AND NOT A PAGE OF CARDS TO SCREENSHOT
 * Because the real use is not somebody deliberately sharing a card. It is
 * somebody pasting a Cedafin link into WhatsApp, which today shows a bare URL
 * and nothing else.
 *
 * Set as og:image, these become what every shared link looks like. The figure
 * travels whether or not anyone decided to share a figure — and in Ghana a
 * link is shared on WhatsApp far more often than anywhere else.
 *
 * WHAT GOES ON A CARD
 * The number, what it is, the source, the date. Nothing else. A card carrying
 * a sentence is a poster, and a poster is advertising; a card carrying a
 * figure and its source is evidence, which is the only thing this site has to
 * offer anybody.
 *
 * WHY THE FIGURES ARE WRITTEN HERE AND NOT READ FROM THE DATABASE
 * Deliberate, and the trade-off is worth stating. Reading live would mean a
 * card can never be stale — but it would also mean a database call inside an
 * image response, on a route that social platforms hit aggressively and cache
 * for weeks.
 *
 * So these carry the date they describe, prominently, and are updated when
 * the underlying figure moves. A card saying "May 2026" is honest a year from
 * now; one saying "today" would not be.
 */

// Node rather than edge — Next deprecated the edge runtime, and an image
// route has no latency requirement that would justify it.
export const runtime = "nodejs";

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  teal: "#1B8BC0",
  gold: "#E8A33D",
  clay: "#C0492B",
  paper: "#F7FAFC",
  muted: "#5F6E78",
};

type Card = {
  eyebrow: string;
  headline: string;
  /** Two figures side by side, which is what makes a comparison legible. */
  left: { value: string; label: string };
  right: { value: string; label: string };
  /** The one line that says why the gap matters. */
  point: string;
  source: string;
};

const CARDS: Record<string, Card> = {
  "lending-spread": {
    eyebrow: "Business credit in Ghana",
    headline: "The same loan, three times the price",
    left: { value: "11.03%", label: "cheapest of 22 banks" },
    right: { value: "33.58%", label: "dearest of 22 banks" },
    point:
      "One-year SME facility, same month. About GH₵22,550 a year of difference on GH₵100,000.",
    source: "Bank of Ghana APR returns, May 2026",
  },
  "broker-commissions": {
    eyebrow: "Buying shares in Ghana",
    headline: "Nobody publishes what a trade costs",
    left: { value: "24", label: "licensed stockbrokers" },
    right: { value: "0", label: "publish a commission rate" },
    point:
      "We visited every one. Comparing costs means contacting firms one by one and asking — there is nothing published to compare.",
    source: "Every dealing member's website, September 2026",
  },
  "gold-premium": {
    eyebrow: "Ghana Gold Coin",
    headline: "The smallest coin costs the most",
    left: { value: "3.46%", label: "premium on one ounce" },
    right: { value: "7.75%", label: "premium on a quarter ounce" },
    point:
      "Same gold, more than twice the markup. The cheapest way in carries the largest premium.",
    source: "Bank of Ghana circulars against LBMA prices, August 2026",
  },
  "tbill-real": {
    eyebrow: "Treasury bills",
    headline: "The safe return is now almost nothing",
    left: { value: "5.08%", label: "91-day Treasury bill" },
    right: { value: "5.0%", label: "inflation" },
    point:
      "Ghana's safest product currently returns close to zero in real terms. Every other return should be read against it.",
    source: "Bank of Ghana auction results and Ghana Statistical Service",
  },
  disclosure: {
    eyebrow: "What Ghanaian funds tell you",
    headline: "Most publish no charge at all",
    left: { value: "6", label: "fund managers publish a charge" },
    right: { value: "44", label: "publish nothing" },
    point:
      "Two funds holding the same instruments can differ by more than two percentage points a year.",
    source: "Provider material against the SEC register, September 2026",
  },
  diaspora: {
    eyebrow: "Investing from abroad",
    headline: "Almost nobody says whether they will take you",
    left: { value: "6", label: "providers state a position" },
    right: { value: "91", label: "say nothing either way" },
    point:
      "Ghanaians abroad sent home US$7.8bn in 2025. Most cannot establish whether a product is open to them.",
    source: "Provider material across funds, brokers and banks, September 2026",
  },
};

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ finding: string }> },
) {
  const { finding } = await params;
  const card = CARDS[finding] ?? CARDS["lending-spread"];

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: C.paper,
          padding: "56px 64px",
          fontFamily: "sans-serif",
          position: "relative",
        }}
      >
        {/* A band rather than a logo. The brand is the source line at the
            bottom; leading with a logo would make this an advertisement. */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 10,
            background: `linear-gradient(90deg, ${C.deep}, ${C.teal})`,
            display: "flex",
          }}
        />

        <div
          style={{
            display: "flex",
            fontSize: 20,
            letterSpacing: 2,
            textTransform: "uppercase",
            color: C.gold,
            fontWeight: 700,
          }}
        >
          {card.eyebrow}
        </div>

        <div
          style={{
            display: "flex",
            fontSize: 52,
            fontWeight: 700,
            color: C.ink,
            marginTop: 12,
            lineHeight: 1.1,
          }}
        >
          {card.headline}
        </div>

        {/* The two figures, which do the work. A reader should be able to take
            the point from these alone at thumbnail size. */}
        <div style={{ display: "flex", gap: 48, marginTop: 40 }}>
          {[card.left, card.right].map((f, i) => (
            <div
              key={f.label}
              style={{
                display: "flex",
                flexDirection: "column",
                flex: 1,
                borderLeft: `6px solid ${i === 0 ? C.deep : C.clay}`,
                paddingLeft: 20,
              }}
            >
              <div
                style={{
                  display: "flex",
                  fontSize: 76,
                  fontWeight: 700,
                  color: i === 0 ? C.deep : C.clay,
                  lineHeight: 1,
                }}
              >
                {f.value}
              </div>
              <div
                style={{
                  display: "flex",
                  fontSize: 22,
                  color: C.muted,
                  marginTop: 10,
                }}
              >
                {f.label}
              </div>
            </div>
          ))}
        </div>

        <div
          style={{
            display: "flex",
            fontSize: 24,
            color: C.ink,
            marginTop: 36,
            lineHeight: 1.4,
          }}
        >
          {card.point}
        </div>

        <div style={{ display: "flex", flex: 1 }} />

        {/* Source and site, same weight. The date is not a footnote — a figure
            without one is the thing this site exists to object to. */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            borderTop: `2px solid #DAE4EB`,
            paddingTop: 18,
          }}
        >
          <div style={{ display: "flex", fontSize: 19, color: C.muted }}>
            {card.source}
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 22,
              fontWeight: 700,
              color: C.deep,
            }}
          >
            cedafin.com
          </div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
