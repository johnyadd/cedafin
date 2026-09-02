/**
 * app/page.tsx — the home page.
 *
 * WHY THREE COLUMNS
 * Modelled on how a market-data site is usually laid out: a ticker across the
 * top, latest writing on the left, the main proposition in the centre, and
 * tools on the right.
 *
 * The right column carries this site's own pages — the matching flows, shares,
 * brokers — rather than advertising. That is deliberate. A comparison site
 * that sells space beside its own rankings has nothing left to sell, and the
 * only reason to visit is that the figures are not for sale. Sponsorship lives
 * on the articles, labelled, and nowhere else.
 *
 * WHAT IS THIN HERE AND WILL FILL
 * The left column shows one article, because one is written. The ticker shows
 * whatever series have data. Both grow without changing the layout, which is
 * the point of building it now rather than twice.
 *
 * WHAT THE CENTRE HAS TO DO
 * Say what this is inside five seconds. Not "financial comparison platform" —
 * a specific figure a visitor cannot get elsewhere, which is why the cheapest
 * and dearest fund charge sit at the top rather than a slogan.
 */

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import SiteHeader from "@/components/SiteHeader";
import Ticker from "@/components/Ticker";
import { BRAND } from "@/lib/brand";
import { getPeerGroups, getPublishedFunds, getTicker } from "@/lib/data/funds";
import { getArticles } from "@/lib/insights";

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
  ink: "#0C1C22",
  deep: "#0B4F6C",
  teal: "#1B8BC0",
  gold: "#E8A33D",
  clay: "#C0492B",
  bg: "#F2F6F9",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
  good: "#0E8F62",
};

const TOOLS: [href: string, title: string, note: string][] = [
  ["/match", "Find what fits you", "Eight questions. Answers stay in your browser."],
  ["/calculator", "Return calculator", "Separates the fund, the currency and the charges."],
  ["/shares", "39 listed shares", "Price history from the exchange's own reports."],
  ["/brokers", "24 stockbrokers", "Not one publishes a commission rate. We checked."],
  ["/compare/commodity-GHS", "Gold, four ways", "The small coin costs twice what the big one does."],
  ["/funding", "Business credit", "22 banks. Advertised rate against what they charge."],
];

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

function toUrl(peerGroup: string): string {
  return peerGroup.replace(":", "-");
}

export const revalidate = 3600;

export default async function Home() {
  const [groups, funds, ticker, articles] = await Promise.all([
    getPeerGroups(),
    getPublishedFunds(),
    getTicker(),
    Promise.resolve(getArticles()),
  ]);

  // Shares excluded: no management charge, so including them would make
  // "cheapest fund" 0.00% and say nothing about what a fund costs.
  const charges = funds
    .filter((f) => f.assetClass !== "equity")
    .map((f) => f.statedChargesPct?.value)
    .filter((v): v is number => typeof v === "number" && v > 0);
  const cheapest = charges.length ? Math.min(...charges) : null;
  const dearest = charges.length ? Math.max(...charges) : null;

  const cheapestIn = new Map<string, number>();
  for (const f of funds) {
    const v = f.statedChargesPct?.value;
    if (!f.peerGroup || typeof v !== "number" || v <= 0) continue;
    const cur = cheapestIn.get(f.peerGroup);
    if (cur === undefined || v < cur) cheapestIn.set(f.peerGroup, v);
  }

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >

      <div className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
        <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)_260px]">
          {/* LEFT — what we have written. */}
          <aside className="order-2 lg:order-1">
            <h2
              className="text-[11px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: C.gold }}
            >
              Insights
            </h2>
            {articles.length === 0 ? (
              <p className="mt-3 text-[13px]" style={{ color: C.muted }}>
                Nothing published yet.
              </p>
            ) : (
              <ul className="mt-3 space-y-2.5">
                {articles.slice(0, 5).map((a) => (
                  <li key={a.slug}>
                    {/*
                      Gold edge and a coloured date, matching the article
                      cards on /insights. Five identical white blocks of text
                      gave the eye nowhere to land.
                    */}
                    <Link
                      href={`/insights/${a.slug}`}
                      className="group flex overflow-hidden rounded-2xl transition-shadow hover:shadow-md"
                      style={{
                        background: C.card,
                        border: `1px solid ${C.rule}`,
                      }}
                    >
                      <span
                        className="w-1 shrink-0"
                        style={{ background: C.gold }}
                        aria-hidden="true"
                      />
                      <span className="flex-1 p-4">
                        <span
                          className="block text-[10px] font-semibold uppercase tracking-[0.12em]"
                          style={{ color: C.gold }}
                        >
                          {fmtDate(a.date)}
                          <span style={{ color: C.muted }}>
                            {" · "}
                            {a.readingMinutes} min
                          </span>
                        </span>
                        <span className="mt-1.5 block text-[13.5px] font-bold leading-snug">
                          {a.title}
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-[12.5px]">
              <Link
                href="/insights"
                className="underline underline-offset-4"
                style={{ color: C.deep }}
              >
                All insights →
              </Link>
            </p>
          </aside>

          {/* CENTRE — what this is, in one figure. */}
          <div className="order-1 lg:order-2">
            {/*
              Back in the centre column, sized to fit. Across the full page
              width the card was too wide to read comfortably and dominated
              everything below it; at this width the three-column rhythm holds
              down the whole page. Smaller type rather than less content.
            */}
            <section
              className="overflow-hidden rounded-3xl p-6 text-white sm:p-7"
              style={{
                background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 72%)`,
              }}
            >
              <h1
                className="text-[1.65rem] font-bold leading-[1.12] sm:text-[2rem]"
                style={{
                  fontFamily: "var(--font-display)",
                  letterSpacing: "-0.015em",
                }}
              >
                Investing and borrowing in Ghana, the opportunities
              </h1>

              <p className="mt-4 text-[13.5px] leading-relaxed opacity-90">
                What Ghanaian funds, Treasury bills, listed shares and gold
                have actually returned, and what business credit really costs
                once fees are counted. Every figure taken from documents
                providers publish themselves, dated and sourced.
              </p>

              <div className="mt-5 grid grid-cols-2 gap-4">
                <div>
                  <p className="text-[9.5px] uppercase tracking-wider opacity-75">
                    Best return we track
                  </p>
                  <p
                    className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none"
                    style={{ color: C.gold }}
                  >
                    +172.7%
                  </p>
                  <p className="mt-1 text-[10px] opacity-70">
                    GSE index, Feb 2025 &ndash; Jul 2026
                  </p>
                </div>
                <div>
                  <p className="text-[9.5px] uppercase tracking-wider opacity-75">
                    Cheapest business credit
                  </p>
                  <p className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none">
                    11.03%
                  </p>
                  <p className="mt-1 text-[10px] opacity-70">
                    APR, of 22 banks
                  </p>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap gap-2.5">
                <Link
                  href="/match"
                  className="rounded-full px-4 py-2.5 text-[13px] font-bold"
                  style={{ background: C.gold, color: C.ink }}
                >
                  Where to invest &rarr;
                </Link>
                <Link
                  href="/funding/match"
                  className="rounded-full px-4 py-2.5 text-[13px] font-bold"
                  style={{ border: "1px solid rgba(255,255,255,0.4)" }}
                >
                  Where to borrow
                </Link>
              </div>
            </section>

            <h2
              className="mt-8 text-[11px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: C.gold }}
            >
              Compare by kind
            </h2>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {groups.map((g) => (
                <Link
                  key={g.peerGroup}
                  href={`/compare/${toUrl(g.peerGroup)}`}
                  className="rounded-2xl p-4"
                  style={{ background: C.card, border: `1px solid ${C.rule}` }}
                >
                  <p className="text-[13.5px] font-bold">{g.label}</p>
                  <p className="mt-1 text-[12px]" style={{ color: C.muted }}>
                    {g.fundCount}{" "}
                    {g.peerGroup.startsWith("equity")
                      ? g.fundCount === 1
                        ? "company"
                        : "companies"
                      : g.peerGroup.startsWith("commodity") ||
                          g.peerGroup.startsWith("government")
                        ? g.fundCount === 1
                          ? "product"
                          : "products"
                        : g.fundCount === 1
                          ? "fund"
                          : "funds"}
                    {cheapestIn.has(g.peerGroup) && (
                      <> · from {cheapestIn.get(g.peerGroup)!.toFixed(2)}%</>
                    )}
                  </p>
                </Link>
              ))}
            </div>

            <section
              className="mt-8 rounded-2xl p-5"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <h2 className="text-[14px] font-bold">
                Where these figures come from
              </h2>
              <p
                className="mt-2 text-[13px] leading-relaxed"
                style={{ color: C.muted }}
              >
                Bank of Ghana&rsquo;s tender results and daily circulars, the
                Ghana Stock Exchange&rsquo;s monthly reports, the SEC&rsquo;s
                registers, and fund managers&rsquo; own factsheets. Nothing here
                is estimated, and where a provider publishes nothing, the page
                says so rather than filling the gap.
              </p>
            </section>

            {/*
              Three figures nobody else publishes.

              The compare-by-kind grid tells a visitor what sections exist. It
              does not tell them why any of it is worth reading.

              Each of these survives the outreach succeeding, which is the
              test for a home page: a gold premium is a price, the index is a
              market fact, and the fee gap comes from the regulator. An
              earlier version led with "0 of 24 brokers publish a rate" —
              true, and wrong the moment one replies.
            */}
            <section className="mt-8">
              <h2
                className="text-[11px] font-semibold uppercase tracking-[0.14em]"
                style={{ color: C.gold }}
              >
                What the numbers show
              </h2>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                {(
                  [
                    [
                      "/insights/gold-coin-premium-ladder",
                      "7.75%",
                      "what the smallest gold coin costs above the metal in it — more than twice the full ounce",
                      C.gold,
                    ],
                    [
                      "/insights/ghanaian-shares-beat-everything",
                      "+172.7%",
                      "the Ghana Stock Exchange index, Feb 2025 to Jul 2026 — on trading volume up 331%",
                      C.good,
                    ],
                    [
                      "/insights/advertised-rate-against-what-you-pay",
                      "9.72pt",
                      "gap between what one bank advertises and what its loan actually costs",
                      "#8A4B1F",
                    ],
                  ] as [string, string, string, string][]
                ).map(([href, figure, note, colour]) => (
                  <Link
                    key={href}
                    href={href}
                    className="group rounded-2xl p-4 transition-shadow hover:shadow-md"
                    style={{ background: C.card, border: `1px solid ${C.rule}` }}
                  >
                    <p
                      className="text-[1.7rem] font-bold tabular-nums leading-none"
                      style={{ color: colour, fontFamily: "var(--font-display)" }}
                    >
                      {figure}
                    </p>
                    <p
                      className="mt-2 text-[12px] leading-relaxed"
                      style={{ color: C.muted }}
                    >
                      {note}
                    </p>
                  </Link>
                ))}
              </div>
            </section>

            {/*
              The borrow side, which was one button in the hero and a card in
              the sidebar — half the site, almost invisible. A business owner
              arriving here had nothing addressed to them.
            */}
            <section
              className="mt-8 overflow-hidden rounded-2xl p-5 text-white sm:p-6"
              style={{
                background: `linear-gradient(135deg, #6B3A16 0%, #A9662E 75%)`,
              }}
            >
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] opacity-80">
                Borrowing
              </p>
              <h2
                className="mt-2 text-[1.4rem] font-bold leading-tight sm:text-[1.7rem]"
                style={{ fontFamily: "var(--font-display)" }}
              >
                The same loan costs 11% at one bank and 34% at another
              </h2>
              <p className="mt-3 text-[13.5px] leading-relaxed opacity-90">
                Bank of Ghana requires every bank to report what its lending
                actually costs, fees included. We publish those figures for 22
                banks. On a one-year SME loan the cheapest and the dearest are
                22.5 percentage points apart — about GH&#8373;22,550 a year on
                GH&#8373;100,000.
              </p>

              <div className="mt-5 grid grid-cols-2 gap-4 sm:max-w-sm">
                <div>
                  <p className="text-[10px] uppercase tracking-wider opacity-75">
                    Cheapest
                  </p>
                  <p
                    className="mt-1 text-[1.5rem] font-bold tabular-nums leading-none"
                    style={{ color: C.gold }}
                  >
                    11.03%
                  </p>
                  <p className="mt-1 text-[10.5px] opacity-70">
                    Standard Chartered
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider opacity-75">
                    Dearest
                  </p>
                  <p className="mt-1 text-[1.5rem] font-bold tabular-nums leading-none">
                    33.58%
                  </p>
                  <p className="mt-1 text-[10.5px] opacity-70">Guaranty Trust</p>
                </div>
              </div>

              {/*
                Nine combinations, because that is what the data holds —
                three kinds of credit at one, three and five years, from Bank
                of Ghana APR returns. /funding already filters on type and
                term, so each lands on the right comparison rather than the
                same page nine times.

                The invest side had a grid like this from the start. The
                borrow side had one button.
              */}
              <div
                className="mt-6 border-t pt-5"
                style={{ borderColor: "rgba(255,255,255,0.25)" }}
              >
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] opacity-75">
                  Compare by kind and term
                </p>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  {(
                    [
                      ["sme_credit", "Business", "22 banks"],
                      ["personal_credit", "Personal", "21 banks"],
                      ["corporate_credit", "Corporate", "21 banks"],
                    ] as [string, string, string][]
                  ).map(([type, label, count]) => (
                    <div key={type}>
                      <p className="text-[12.5px] font-bold">{label}</p>
                      <p className="text-[10.5px] opacity-70">{count}</p>
                      <div className="mt-1.5 flex gap-1.5">
                        {[1, 3, 5].map((term) => (
                          <Link
                            key={term}
                            href={`/funding?type=${type}&term=${term}`}
                            className="rounded-full px-2.5 py-1 text-[11.5px] font-semibold"
                            style={{
                              background: "rgba(255,255,255,0.15)",
                              border: "1px solid rgba(255,255,255,0.25)",
                            }}
                          >
                            {term}yr
                          </Link>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/*
                Borrowing reading, inside the borrowing section.

                The Insights column lists the five most recent articles
                regardless of subject, and a side column does not move with
                the reader. Putting the relevant pieces here means they sit
                where someone is already looking.
              */}
              <div
                className="mt-5 border-t pt-4"
                style={{ borderColor: "rgba(255,255,255,0.25)" }}
              >
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] opacity-75">
                  Worth reading first
                </p>
                <ul className="mt-2 space-y-1.5">
                  {(
                    [
                      [
                        "/insights/how-to-borrow-for-your-business-in-ghana",
                        "How to borrow for your business in Ghana",
                      ],
                      [
                        "/insights/advertised-rate-against-what-you-pay",
                        "One bank advertises 13.70% and charges 23.42%",
                      ],
                    ] as [string, string][]
                  ).map(([href, label]) => (
                    <li key={href}>
                      <Link
                        href={href}
                        className="text-[12.5px] underline underline-offset-4 opacity-90 hover:opacity-100"
                      >
                        {label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mt-5 flex flex-wrap gap-2.5">
                <Link
                  href="/funding"
                  className="rounded-full px-4 py-2.5 text-[13px] font-bold"
                  style={{ background: C.gold, color: C.ink }}
                >
                  Compare all 22 banks &rarr;
                </Link>
                <Link
                  href="/funding/match"
                  className="rounded-full px-4 py-2.5 text-[13px] font-bold"
                  style={{ border: "1px solid rgba(255,255,255,0.4)" }}
                >
                  Find funding that fits
                </Link>
              </div>
            </section>
          </div>

          {/* RIGHT — our own tools, not advertising. */}
          <aside className="order-3">
            <h2
              className="text-[11px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: C.gold }}
            >
              Tools
            </h2>
            <ul className="mt-3 space-y-2.5">
              {TOOLS.map(([href, title, note], i) => {
                /*
                  A coloured edge per tool, keyed to what it is rather than
                  assigned at random — gold for gold, brown for borrowing, the
                  brand blue for the rest. A column of identical white cards
                  gave a reader nothing to aim at.
                */
                const edge = href.includes("commodity")
                  ? C.gold
                  : href.includes("funding")
                    ? "#8A4B1F"
                    : href.includes("shares") || href.includes("brokers")
                      ? C.teal
                      : C.deep;
                return (
                  <li key={href}>
                    <Link
                      href={href}
                      className="group flex overflow-hidden rounded-2xl transition-shadow hover:shadow-md"
                      style={{
                        background: C.card,
                        border: `1px solid ${C.rule}`,
                      }}
                    >
                      <span
                        className="w-1 shrink-0"
                        style={{ background: edge }}
                        aria-hidden="true"
                      />
                      <span className="flex-1 p-4">
                        <span className="flex items-baseline gap-1.5">
                          <span className="text-[13.5px] font-bold">{title}</span>
                          <span
                            className="ml-auto text-[13px] opacity-0 transition-opacity group-hover:opacity-100"
                            style={{ color: edge }}
                          >
                            &rarr;
                          </span>
                        </span>
                        <span
                          className="mt-1 block text-[11.5px] leading-relaxed"
                          style={{ color: C.muted }}
                        >
                          {note}
                        </span>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>

            {/*
              The ask, on the busiest page. Most of what is missing from this
              site is missing because nobody publishes it, and a provider
              landing here should find the invitation without hunting.
            */}
            <section
              className="mt-6 rounded-2xl p-4"
              style={{ background: C.card, border: `1px solid ${C.gold}` }}
            >
              <p className="text-[12.5px] font-bold">
                If you run one of these firms
              </p>
              <p
                className="mt-1.5 text-[11.5px] leading-relaxed"
                style={{ color: C.muted }}
              >
                Send us what you publish and we will show it beside your name,
                cited and dated. We would rather be corrected than wrong.
              </p>
              <p className="mt-2 text-[12px] font-semibold">
                <a
                  href={`mailto:${BRAND.dataEmail}`}
                  className="underline underline-offset-4"
                  style={{ color: C.deep }}
                >
                  {BRAND.dataEmail}
                </a>
              </p>
            </section>
          </aside>
        </div>
      </div>

      <Footer />
    </main>
  );
}
