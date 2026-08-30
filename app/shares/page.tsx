/**
 * app/shares/page.tsx — Ghanaian listed shares, and what they actually did.
 *
 * WHY SHARES GET THEIR OWN PAGE RATHER THAN A COMPARISON GROUP
 * Ranking a single company beside a diversified fund on cost would put every
 * share top — they carry no management charge — while the real cost is
 * brokerage nobody publishes and the real difference is concentration risk.
 * The comparison pages exist to put like beside like. This is not like.
 *
 * A CORRECTION THIS PAGE WAS BUILT ON, THEN REBUILT AFTER
 * The July 2026 report shows volume down 71.98% year on year, and the first
 * draft of this page led with it: a market rising on collapsing trade, prices
 * moving because nobody was selling. That framing was wrong.
 *
 * Fifteen months of the exchange's own reports say the opposite. February 2025
 * to July 2026: the index rose 172.7% and volume rose 331.2%. Both climbing is
 * the healthy version — prices up because more people are buying. The
 * year-on-year figure measured one month against an exceptional July 2025.
 *
 * A snapshot said one thing and a series said another, and the series wins.
 * Worth recording, because a page warning savers off the best-performing asset
 * in Ghana on the strength of a single month would have been a real harm.
 *
 * DIVIDENDS ARE MISSING, AND THE DIRECTION OF THE ERROR IS KNOWN
 * Every figure here is a price move. The GSE monthly report does not publish
 * dividends — its glossary defines dividend yield and then prints it for no
 * company. So these understate what a holder received. A number wrong in a
 * knowable direction should say which direction, so the page does.
 */

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import { BRAND } from "@/lib/brand";
import Spark from "@/components/Spark";
import { getEquities, type EquityRow } from "@/lib/data/funds";

const display = Fraunces({
  subsets: ["latin"],
  weight: "variable",
  axes: ["SOFT", "WONK", "opsz"],
  variable: "--font-display",
});
const body = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
});

const C = {
  ink: "#0C1F1C",
  deep: "#0A5D52",
  teal: "#128B7A",
  gold: "#E8A33D",
  clay: "#C0492B",
  bg: "#F3F6F3",
  card: "#FFFFFF",
  rule: "#DCE5E0",
  muted: "#5F726C",
  good: "#0E8F62",
};

const GHS = new Intl.NumberFormat("en-GH", {
  style: "currency",
  currency: "GHS",
  maximumFractionDigits: 2,
});

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

/**
 * A sparkline drawn from the monthly closes. Deliberately unlabelled and
 * small: it shows shape, not values. Someone wanting the numbers has them
 * beside it, and a chart pretending to more precision than fifteen monthly
 * points support would be decoration rather than information.
 */
export const revalidate = 3600;

export default async function SharesPage() {
  const shares = await getEquities();
  const withMove = shares.filter((s) => s.priceMovePct !== null);
  const risers = withMove.filter((s) => (s.priceMovePct ?? 0) > 0).length;
  const period = withMove[0];

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div
        className="w-full px-5 py-2 text-center text-[11px] font-medium tracking-wide text-white"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        {shares.length} listed shares · prices from the exchange&rsquo;s own
        monthly reports
      </div>

      <header className="mx-auto max-w-4xl px-5 pt-6 sm:px-8">
        <Link
          href="/"
          className="text-[19px] font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: C.deep }}
        >
          {BRAND.name}
        </Link>
      </header>

      <div className="mx-auto max-w-4xl px-5 py-8 sm:px-8 sm:py-10">
        <section
          className="overflow-hidden rounded-3xl p-7 text-white sm:p-10"
          style={{
            background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 72%)`,
          }}
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-80">
            Ghana Stock Exchange
          </p>
          <h1
            className="mt-3 text-[2.1rem] font-bold leading-[1.08] sm:text-[3rem]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            The best returns
            <br />
            in Ghana, and more
            <br />
            people buying.
          </h1>

          <div className="mt-8 grid grid-cols-2 gap-4 sm:max-w-md">
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Index, Feb 2025 – Jul 2026
              </p>
              <p
                className="mt-1 text-[1.8rem] font-bold tabular-nums leading-none sm:text-[2.2rem]"
                style={{ color: C.gold }}
              >
                +172.7%
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Shares traded
              </p>
              <p className="mt-1 text-[1.8rem] font-bold tabular-nums leading-none sm:text-[2.2rem]">
                +331.2%
              </p>
            </div>
          </div>

          <p className="mt-7 max-w-xl text-[14px] leading-relaxed opacity-90">
            Ghanaian shares rose faster than any fund, bill or gold product we
            track, and trading more than quadrupled over the same period. Prices
            rose because more people were buying — not because fewer were
            selling into a thin market.
          </p>
        </section>

        {/* Everything the site tracks, on one scale. */}
        <section
          className="mt-6 rounded-2xl p-5 sm:p-6"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2 className="text-[15px] font-bold">
            Against everything else on this site
          </h2>
          <ul className="mt-3 space-y-1.5 text-[13.5px]">
            {[
              ["GSE Composite Index", "+172.7%", "Feb 2025 – Jul 2026", C.good],
              ["Stanbic Income Fund Trust", "+38.80%", "1 year", C.ink],
              ["First Atlantic Income Fund", "+34.73%", "1 year", C.ink],
              ["364-day Treasury bill", "+11.59%", "current rate", C.ink],
              ["91-day Treasury bill", "+5.08%", "current rate", C.ink],
              ["Ghana Gold Coin, 1 oz", "−3.93%", "in cedis, Jun–Aug", C.clay],
            ].map(([name, val, note, colour]) => (
              <li key={name as string} className="flex flex-wrap gap-x-3">
                <span className="min-w-[13rem] flex-1">{name}</span>
                <span
                  className="font-bold tabular-nums"
                  style={{ color: colour as string }}
                >
                  {val}
                </span>
                <span className="text-[12px]" style={{ color: C.muted }}>
                  {note}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-[12.5px]" style={{ color: C.muted }}>
            Different periods and different risks — a single share is not a
            diversified fund, and none of these is a forecast. Shown together
            because a saver comparing them deserves to see them on one scale
            rather than four separate pages.
          </p>
        </section>

        <h2
          className="mt-12 text-[24px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Every listed share
        </h2>
        <p className="mt-2 max-w-2xl text-[13.5px]" style={{ color: C.muted }}>
          {risers} of {withMove.length} rose over the period held
          {period?.firstSeen && period?.lastSeen && (
            <>
              {" "}
              ({fmtDate(period.firstSeen)} – {fmtDate(period.lastSeen)})
            </>
          )}
          . Price only — dividends are not published by the exchange, so these
          understate what a holder actually received.
        </p>

        <ol className="mt-5 space-y-2.5">
          {shares.map((s) => {
            const up = (s.priceMovePct ?? 0) >= 0;
            return (
              <li
                key={s.slug}
                className="rounded-2xl p-4 sm:p-5"
                style={{ background: C.card, border: `1px solid ${C.rule}` }}
              >
                <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
                  <div className="min-w-0">
                    <h3 className="text-[14.5px] font-bold">{s.ticker}</h3>
                    <p className="mt-0.5 text-[12px]" style={{ color: C.muted }}>
                      {s.sector}
                      {s.latestPrice !== null && (
                        <> · {GHS.format(s.latestPrice)} a share</>
                      )}
                    </p>
                  </div>

                  <div className="flex items-center gap-4">
                    <Spark points={s.prices} caption={false} minPoints={4} />
                    <div className="text-right">
                      <p
                        className="text-[1.15rem] font-bold tabular-nums leading-none"
                        style={{ color: up ? C.good : C.clay }}
                      >
                        {up ? "+" : ""}
                        {s.priceMovePct?.toFixed(1)}%
                      </p>
                      <p className="text-[10.5px]" style={{ color: C.muted }}>
                        {s.months} months
                      </p>
                    </div>
                  </div>
                </div>

                {(s.marketCapGhsMil !== null || s.peRatio !== null) && (
                  <p className="mt-3 text-[12px]" style={{ color: C.muted }}>
                    {s.marketCapGhsMil !== null && (
                      <>
                        Worth GH&#8373;
                        {s.marketCapGhsMil >= 1000
                          ? `${(s.marketCapGhsMil / 1000).toFixed(1)}bn`
                          : `${s.marketCapGhsMil.toFixed(0)}m`}
                      </>
                    )}
                    {s.peRatio !== null && (
                      <>
                        {s.marketCapGhsMil !== null ? " · " : ""}
                        P/E {s.peRatio.toFixed(1)}
                      </>
                    )}
                  </p>
                )}
              </li>
            );
          })}
        </ol>

        <section
          className="mt-12 rounded-3xl p-6 sm:p-8"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2
            className="text-[18px] font-bold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            What this page doesn&rsquo;t show
          </h2>
          <ul
            className="mt-4 space-y-3 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            <li>
              <strong style={{ color: C.ink }}>Dividends.</strong> The
              exchange&rsquo;s monthly report defines dividend yield in its
              glossary and publishes it for no company. Every figure above is a
              price move only, so all of them understate what a holder
              received.
            </li>
            <li>
              <strong style={{ color: C.ink }}>What it costs to buy.</strong>{" "}
              Brokerage, charged by whichever licensed dealing member you use.
              None of the twenty-four publishes a rate.
            </li>
            <li>
              <strong style={{ color: C.ink }}>
                Whether you could sell at these prices.
              </strong>{" "}
              Trading has risen sharply — shares traded are up 331% since
              February 2025 — but the Ghana Stock Exchange remains small. A
              quoted price is what the last trade happened at, and in any
              individual share that may have been some time ago.
            </li>
            <li>
              <strong style={{ color: C.ink }}>Anything about the company.</strong>{" "}
              Earnings, debt, management, sector conditions. A share is a claim
              on a business, and this page shows only what its price did.
            </li>
          </ul>

          <p className="mt-6 text-[13.5px]">
            <Link
              href="/brokers"
              className="font-semibold underline underline-offset-4"
              style={{ color: C.deep }}
            >
              You&rsquo;ll need a broker →
            </Link>
          </p>

          <p className="mt-6 text-[11px] leading-relaxed" style={{ color: C.muted }}>
            {BRAND.legalStatus} Prices are taken from the Ghana Stock
            Exchange&rsquo;s published monthly reports.
          </p>
        </section>
      </div>
    </main>
  );
}
