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
};

const TOOLS: [href: string, title: string, note: string][] = [
  ["/match", "Find what fits you", "Eight questions. Answers stay in your browser."],
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
              <ul className="mt-3 space-y-3">
                {articles.slice(0, 5).map((a) => (
                  <li
                    key={a.slug}
                    className="rounded-2xl p-4"
                    style={{ background: C.card, border: `1px solid ${C.rule}` }}
                  >
                    <p className="text-[10.5px]" style={{ color: C.muted }}>
                      {fmtDate(a.date)} · {a.readingMinutes} min
                    </p>
                    <Link
                      href={`/insights/${a.slug}`}
                      className="mt-1 block text-[13.5px] font-bold leading-snug"
                    >
                      {a.title}
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
                Investing and borrowing in Ghana,
                <br />
                the opportunities
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
          </div>

          {/* RIGHT — our own tools, not advertising. */}
          <aside className="order-3">
            <h2
              className="text-[11px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: C.gold }}
            >
              Tools
            </h2>
            <ul className="mt-3 space-y-3">
              {TOOLS.map(([href, title, note]) => (
                <li key={href}>
                  <Link
                    href={href}
                    className="block rounded-2xl p-4"
                    style={{ background: C.card, border: `1px solid ${C.rule}` }}
                  >
                    <p className="text-[13.5px] font-bold">{title}</p>
                    <p
                      className="mt-1 text-[11.5px] leading-relaxed"
                      style={{ color: C.muted }}
                    >
                      {note}
                    </p>
                  </Link>
                </li>
              ))}
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
