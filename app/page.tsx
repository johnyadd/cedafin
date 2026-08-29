/**
 * app/page.tsx — the split home page.
 *
 * TWO AUDIENCES WHO WANT OPPOSITE THINGS
 * A saver with GH¢1,000 choosing a fund, and a business seeking GH¢200,000 of
 * credit. Same market, same regulator-published data, entirely different
 * question. The previous version of this page addressed only the first and
 * never mentioned the second — someone landing here would not have known the
 * funding side existed.
 *
 * So: two routes above the fold, equal weight, and the visitor self-selects.
 * That is what two-sided comparison sites do, and pretending there is one
 * audience would serve neither.
 *
 * EVERY NUMBER HERE COMES FROM THE DATABASE.
 * No hardcoded claims. If coverage changes, the page changes. The spread that
 * headlines the funding route is computed from the loaded products, not typed
 * in — because a marketing figure that drifts from the data is exactly the
 * failure this whole site is built against.
 *
 * THE COVERAGE GAP IS STATED, NOT HIDDEN.
 * "7 of 72 verified" and "banks only" both appear. Most comparison sites bury
 * that. Leading with it costs something with a first-time visitor and buys the
 * thing that matters more: a fund manager or a bank reading this can see
 * immediately that we describe our own limits accurately.
 */

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import { BRAND } from "@/lib/brand";
import {
  getDirectory,
  getLending,
  getPeerGroups,
  getPublishedFunds,
} from "@/lib/data/funds";

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
  maximumFractionDigits: 0,
});

const toUrl = (peerGroup: string) => peerGroup.replace(/:([^:]*)$/, "-$1");

export const revalidate = 3600;

export default async function HomePage() {
  const [funds, directory, groups, sme] = await Promise.all([
    getPublishedFunds(),
    getDirectory(),
    getPeerGroups(),
    getLending("sme_credit"),
  ]);

  const unique = [
    ...new Map(funds.map((f) => [`${f.provider.slug}::${f.name}`, f])).values(),
  ];
  // Treasury bills charge nothing, so an unfiltered minimum reports 0.00% —
  // true, and useless as a headline about what FUNDS cost. A saver reading
  // "charges from 0.00%" would expect a free fund and find none.
  const charges = unique
    .filter((f) => f.assetClass !== "government_security")
    .map((f) => f.statedChargesPct?.value)
    .filter((v): v is number => typeof v === "number" && v > 0);
  const cheapestFund = charges.length ? Math.min(...charges) : null;
  const lowestMin = unique
    .map((f) => f.minimumGhs?.value)
    .filter((v): v is number => typeof v === "number")
    .sort((a, b) => a - b)[0];
  const totalFunds = unique.length + directory.length;

  // One-year SME credit: the sharpest comparison the site can make.
  const oneYear = sme.filter((r) => r.tenorYears === 1);
  const aprs = oneYear.map((r) => r.aprPct).filter((v): v is number => v !== null);
  const loLoan = aprs.length ? Math.min(...aprs) : null;
  const hiLoan = aprs.length ? Math.max(...aprs) : null;
  const lenderCount = new Set(sme.map((r) => r.provider.slug)).size;

  // The single most useful fact on the site: a bank whose advertised rate is
  // far below what it actually charges. Found, not asserted.
  const biggestGap = [...oneYear]
    .filter((r) => r.feeGapPct !== null)
    .sort((a, b) => (b.feeGapPct ?? 0) - (a.feeGapPct ?? 0))[0];

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div
        className="w-full px-5 py-2 text-center text-[11px] font-medium tracking-wide text-white"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        {totalFunds} funds and {sme.length} bank credit facilities tracked ·
        every figure dated and sourced
      </div>

      <header className="mx-auto max-w-5xl px-5 pt-6 sm:px-8">
        <span
          className="text-[19px] font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: C.deep }}
        >
          {BRAND.name}
        </span>
      </header>

      <div className="mx-auto max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
        <h1
          className="max-w-3xl text-[2.1rem] font-bold leading-[1.06] sm:text-[3.2rem]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Ghana&rsquo;s money market,
          <br />
          with the prices shown.
        </h1>
        <p
          className="mt-5 max-w-2xl text-[15px] leading-relaxed"
          style={{ color: C.muted }}
        >
          We read what providers and Bank of Ghana publish, and put the numbers
          side by side — charges, rates, minimums, and the date each figure was
          confirmed. Whether you&rsquo;re putting money in or taking it out.
        </p>

        {/*
          Entry to the matching flow, above the two route cards.

          Placed here deliberately: a visitor who already knows they want to
          compare fund charges will scroll straight to the cards. A visitor who
          does not know what they are looking for — which is most first-time
          savers — needs a way in that does not require them to have decided
          anything first. Burying it below the cards would serve only the
          people who least need it.
        */}
        <Link
          href="/match"
          className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded-2xl px-6 py-5"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <div>
            <p
              className="text-[11px] font-semibold uppercase tracking-[0.16em]"
              style={{ color: C.teal }}
            >
              Not sure where to start
            </p>
            <p className="mt-1.5 text-[15.5px] font-bold">
              Answer eight questions, see what actually fits
            </p>
            <p className="mt-1 text-[12.5px]" style={{ color: C.muted }}>
              How much you have, when you need it back, what you&rsquo;re
              comfortable with. Nothing is saved.
            </p>
          </div>
          <span
            className="shrink-0 rounded-full px-5 py-2.5 text-[13.5px] font-bold text-white"
            style={{ background: C.deep }}
          >
            Start →
          </span>
        </Link>

        {/* THE SPLIT. Two routes, equal weight, visitor self-selects. */}
        <div className="mt-10 grid gap-5 lg:grid-cols-2">
          {/* Invest */}
          <Link
            href="/funds"
            className="group overflow-hidden rounded-3xl p-7 text-white transition-transform sm:p-8"
            style={{
              background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 75%)`,
            }}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-80">
              I have money to invest
            </p>
            <h2
              className="mt-3 text-[1.7rem] font-bold leading-tight sm:text-[2.1rem]"
              style={{ fontFamily: "var(--font-display)" }}
            >
              What funds
              <br />
              really cost
            </h2>
            <p className="mt-4 text-[13.5px] leading-relaxed opacity-90">
              Money market, fixed income and balanced funds compared on the
              charges every provider publishes — plus Treasury bills, which
              charge nothing at all.
            </p>

            <div className="mt-7 flex flex-wrap gap-6">
              {cheapestFund !== null && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider opacity-70">
                    Charges from
                  </p>
                  <p
                    className="mt-1 text-[1.5rem] font-bold tabular-nums leading-none"
                    style={{ color: C.gold }}
                  >
                    {cheapestFund.toFixed(2)}%
                  </p>
                </div>
              )}
              {lowestMin !== undefined && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider opacity-70">
                    Start from
                  </p>
                  <p className="mt-1 text-[1.5rem] font-bold tabular-nums leading-none">
                    {GHS.format(lowestMin)}
                  </p>
                </div>
              )}
              <div>
                <p className="text-[10px] uppercase tracking-wider opacity-70">
                  Funds tracked
                </p>
                <p className="mt-1 text-[1.5rem] font-bold tabular-nums leading-none">
                  {totalFunds}
                  <span className="text-[0.95rem] opacity-60">
                    {" "}
                    · {unique.length} verified
                  </span>
                </p>
              </div>
            </div>

            <p className="mt-7 text-[13.5px] font-bold underline underline-offset-4">
              Compare funds →
            </p>
          </Link>

          {/* Borrow */}
          <Link
            href="/funding"
            className="group overflow-hidden rounded-3xl p-7 text-white transition-transform sm:p-8"
            style={{
              background: `linear-gradient(135deg, #7A3E12 0%, ${C.gold} 145%)`,
            }}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-80">
              My business needs funding
            </p>
            <h2
              className="mt-3 text-[1.7rem] font-bold leading-tight sm:text-[2.1rem]"
              style={{ fontFamily: "var(--font-display)" }}
            >
              What credit
              <br />
              really costs
            </h2>
            <p className="mt-4 text-[13.5px] leading-relaxed opacity-90">
              Every licensed bank&rsquo;s lending rates, published by Bank of
              Ghana — with the fees that a headline rate leaves out.
            </p>

            <div className="mt-7 flex flex-wrap gap-6">
              {loLoan !== null && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider opacity-70">
                    SME credit from
                  </p>
                  <p className="mt-1 text-[1.5rem] font-bold tabular-nums leading-none">
                    {loLoan.toFixed(2)}%
                  </p>
                </div>
              )}
              {hiLoan !== null && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider opacity-70">
                    Up to
                  </p>
                  <p className="mt-1 text-[1.5rem] font-bold tabular-nums leading-none">
                    {hiLoan.toFixed(2)}%
                  </p>
                </div>
              )}
              <div>
                <p className="text-[10px] uppercase tracking-wider opacity-70">
                  Banks compared
                </p>
                <p className="mt-1 text-[1.5rem] font-bold tabular-nums leading-none">
                  {lenderCount}
                </p>
              </div>
            </div>

            <p className="mt-7 text-[13.5px] font-bold underline underline-offset-4">
              Compare business credit →
            </p>
          </Link>
        </div>

        {/* The finding. Computed, not asserted. */}
        {biggestGap && biggestGap.feeGapPct !== null && biggestGap.feeGapPct > 3 && (
          <section
            className="mt-10 rounded-3xl p-6 sm:p-8"
            style={{ background: C.card, border: `1px solid ${C.rule}` }}
          >
            <p
              className="text-[11px] font-semibold uppercase tracking-[0.16em]"
              style={{ color: C.clay }}
            >
              Why the headline rate isn&rsquo;t the price
            </p>
            <p
              className="mt-3 max-w-3xl text-[16px] leading-relaxed"
              style={{ fontFamily: "var(--font-display)" }}
            >
              {biggestGap.provider.name} advertises{" "}
              <strong>{biggestGap.lendingRatePct?.toFixed(2)}%</strong> on a
              one-year business loan. Once its charges are counted, the real cost
              is <strong>{biggestGap.aprPct?.toFixed(2)}%</strong> — a gap of{" "}
              {biggestGap.feeGapPct.toFixed(1)} percentage points that no
              advertised rate shows you.
            </p>
            <p className="mt-4 text-[13px]" style={{ color: C.muted }}>
              Bank of Ghana publishes both figures. We put them next to each
              other.
            </p>
          </section>
        )}

        {/* Why trust it */}
        <h2
          className="mt-14 text-[22px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Why trust these numbers
        </h2>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {[
            {
              t: "Every figure is dated",
              d: "Each charge and rate shows the document it came from and when it was last confirmed. If a number is six months old, we say so.",
            },
            {
              t: "Like compared with like",
              d: "Not every provider publishes the same fields, so we compare on what they all disclose — and name what's missing.",
            },
            {
              t: "Nobody can pay for position",
              d: "We don't charge to be listed and no provider can buy a ranking. We say when a group is too small to rank at all.",
            },
            {
              t: "Gaps are shown, not hidden",
              d: `${directory.length} funds are listed with no figures, and our credit data covers banks only. Leaving either out would make our coverage look better than it is.`,
            },
          ].map((x) => (
            <div
              key={x.t}
              className="rounded-2xl p-5"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <h3 className="text-[14.5px] font-bold">{x.t}</h3>
              <p
                className="mt-1.5 text-[12.5px] leading-relaxed"
                style={{ color: C.muted }}
              >
                {x.d}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/match"
            className="rounded-full px-5 py-2.5 text-[13.5px] font-bold text-white"
            style={{ background: C.teal }}
          >
            Find what fits →
          </Link>
          <Link
            href="/funds"
            className="rounded-full px-5 py-2.5 text-[13.5px] font-bold text-white"
            style={{ background: C.deep }}
          >
            All {totalFunds} funds →
          </Link>
          <Link
            href="/funding"
            className="rounded-full px-5 py-2.5 text-[13.5px] font-bold text-white"
            style={{ background: "#7A3E12" }}
          >
            Business credit →
          </Link>
          {groups.slice(0, 2).map((g) => (
            <Link
              key={g.peerGroup}
              href={`/compare/${toUrl(g.peerGroup)}`}
              className="rounded-full px-4 py-2.5 text-[13px] font-semibold"
              style={{
                background: C.card,
                color: C.ink,
                border: `1px solid ${C.rule}`,
              }}
            >
              {g.label}
            </Link>
          ))}
        </div>

        <section
          className="mt-14 rounded-3xl p-6 sm:p-8"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2
            className="text-[18px] font-bold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            If you run a fund or a lending book
          </h2>
          <p
            className="mt-3 max-w-2xl text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            We publish from your own documents and cite them beside every
            figure. If your product is listed with blanks against it, send your
            factsheet or rate card and we&rsquo;ll show your figures instead of
            our gaps. Corrections are free and applied the same day.
          </p>
          <p className="mt-4 text-[14px] font-semibold">
            <a
              href={`mailto:${BRAND.dataEmail}`}
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              {BRAND.dataEmail}
            </a>
          </p>
          <p className="mt-6 text-[11px] leading-relaxed" style={{ color: C.muted }}>
            {BRAND.legalStatus} We are not a credit broker and do not arrange
            finance. Past performance does not predict future returns, and the
            value of an investment can fall as well as rise. Lending rates shown
            are indicative and not offers.
          </p>
        </section>
      </div>
    </main>
  );
}
