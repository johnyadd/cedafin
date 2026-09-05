/**
 * app/page.tsx — the home page.
 *
 * WHY TWO THREE-COLUMN BLOCKS RATHER THAN ONE
 * The page started as a single grid: articles left, everything else centre,
 * tools right. That worked while the site was about investing.
 *
 * It stopped working once the borrowing section arrived. The side columns are
 * short, so they ended well above it — the borrow card sat in the middle of
 * the page with empty space either side, and the "Insights" column listed
 * whatever was most recent regardless of whether it had anything to do with
 * borrowing.
 *
 * So there are two blocks now, each with its own heading, its own articles and
 * its own tools. A visitor who came to borrow gets a section addressed to
 * them rather than a card wedged into somebody else's layout.
 *
 * HOW THE SPLIT IS DECIDED
 * By article tag, which already exists in the frontmatter. Anything tagged
 * lending, banks or SME is borrowing; everything else is investing. No new
 * field, no manual list to maintain, and a new article lands in the right
 * column by virtue of how it was tagged.
 *
 * WHAT THE RIGHT COLUMN CARRIES
 * This site's own pages, not advertising. A comparison site that sells space
 * beside its own rankings has nothing left to sell, and the only reason to
 * visit is that the figures are not for sale. Sponsorship lives on the
 * articles, labelled, and nowhere else.
 */

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Faq from "@/components/Faq";
import Footer from "@/components/Footer";
import Subscribe from "@/components/Subscribe";
import { BRAND } from "@/lib/brand";
import { getPeerGroups, getPublishedFunds } from "@/lib/data/funds";
import { getArticles, type Article } from "@/lib/insights";

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
  /** The borrow side, everywhere. Brown so the two halves never blur. */
  brownDeep: "#6B3A16",
  brown: "#8A4B1F",
  brownLight: "#A9662E",
};

type Tool = [href: string, title: string, note: string];

const INVEST_TOOLS: Tool[] = [
  ["/match", "Find what fits you", "Eight questions. Answers stay in your browser."],
  ["/calculator", "Returns calculator", "Separates the fund, the currency and the charges."],
  ["/inflation-calculator", "Inflation calculator", "What your cedis were worth, back to 1964."],
  ["/shares", "39 listed shares", "Price history from the exchange's own reports."],
  ["/brokers", "24 stockbrokers", "Not one publishes a commission rate. We checked."],
  ["/compare/commodity-GHS", "Gold, four ways", "The small coin costs twice what the big one does."],
];

const BORROW_TOOLS: Tool[] = [
  ["/funding", "Compare 22 banks", "What each actually charges, fees included."],
  ["/funding/match", "Find funding that fits", "Six questions. Nothing saved."],
  ["/loan-calculator", "Loan calculator", "What a loan costs, at each of 22 banks."],
];

/**
 * Which side an article belongs to.
 *
 * Read from tags rather than a hand-kept list, so a new piece lands in the
 * right column by virtue of how it was tagged rather than because somebody
 * remembered to add it here.
 */
const BORROW_TAGS = ["lending", "banks", "SME"];
const isBorrowArticle = (a: Article) =>
  a.tags.some((t) => BORROW_TAGS.includes(t));

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

/** One article card. Same shape both sides; only the edge colour differs. */
function ArticleCard({ a, edge }: { a: Article; edge: string }) {
  return (
    <li>
      <Link
        href={`/insights/${a.slug}`}
        className="group flex overflow-hidden rounded-2xl transition-shadow hover:shadow-md"
        style={{ background: C.card, border: `1px solid ${C.rule}` }}
      >
        <span
          className="w-1 shrink-0"
          style={{ background: edge }}
          aria-hidden="true"
        />
        <span className="flex-1 p-4">
          <span
            className="block text-[10px] font-semibold uppercase tracking-[0.12em]"
            style={{ color: edge }}
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
  );
}

/** One tool card. */
function ToolCard({ href, title, note, edge }: {
  href: string;
  title: string;
  note: string;
  edge: string;
}) {
  return (
    <li>
      <Link
        href={href}
        className="group flex overflow-hidden rounded-2xl transition-shadow hover:shadow-md"
        style={{ background: C.card, border: `1px solid ${C.rule}` }}
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
}

/** The heading that separates the two halves of the site. */
function SectionHead({
  label,
  colour,
  note,
}: {
  label: string;
  colour: string;
  note: string;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <h2
        className="text-[1.3rem] font-bold"
        style={{ fontFamily: "var(--font-display)", color: colour }}
      >
        {label}
      </h2>
      <p className="text-[12.5px]" style={{ color: C.muted }}>
        {note}
      </p>
      <span
        className="mt-2 block h-[3px] w-full"
        style={{ background: colour, opacity: 0.25 }}
        aria-hidden="true"
      />
    </div>
  );
}

export const revalidate = 3600;

export default async function Home() {
  const [groups, funds, articles] = await Promise.all([
    getPeerGroups(),
    getPublishedFunds(),
    Promise.resolve(getArticles()),
  ]);

  const borrowArticles = articles.filter(isBorrowArticle).slice(0, 4);
  const investArticles = articles.filter((a) => !isBorrowArticle(a)).slice(0, 5);

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

  // items-start matters: without it a grid child stretches to the row
  // height, so a sticky aside has no room to move within its own cell and
  // simply never sticks.
  const grid =
    "grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)_260px] lg:items-start";
  const eyebrow =
    "text-[11px] font-semibold uppercase tracking-[0.14em]";

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
        {/* ───────────────────────── INVESTING ───────────────────────── */}
        <SectionHead
          label="Investing"
          colour={C.deep}
          note="Funds, Treasury bills, listed shares and gold — what each costs and what it returned"
        />

        <div className={grid}>
          <aside className="order-2 lg:sticky lg:top-[76px] lg:order-1">
            <h3 className={eyebrow} style={{ color: C.gold }}>
              Reading
            </h3>
            {investArticles.length === 0 ? (
              <p className="mt-3 text-[13px]" style={{ color: C.muted }}>
                Nothing published yet.
              </p>
            ) : (
              <ul className="mt-3 space-y-2.5">
                {investArticles.map((a) => (
                  <ArticleCard key={a.slug} a={a} edge={C.gold} />
                ))}
              </ul>
            )}
            <p className="mt-3 text-[12.5px]">
              <Link
                href="/insights"
                className="underline underline-offset-4"
                style={{ color: C.deep }}
              >
                All insights &rarr;
              </Link>
            </p>

          </aside>

          <div className="order-1 lg:order-2">
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
                What Ghanaian funds, Treasury bills, listed shares and gold have
                actually returned, and what business credit really costs once
                fees are counted. Every figure taken from documents providers
                publish themselves, dated and sourced.
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
                  <p className="mt-1 text-[10px] opacity-70">APR, of 22 banks</p>
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

            <h3 className={`mt-8 ${eyebrow}`} style={{ color: C.gold }}>
              Compare by kind
            </h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {groups.map((g) => (
                <Link
                  key={g.peerGroup}
                  href={`/compare/${toUrl(g.peerGroup)}`}
                  className="rounded-2xl p-4 transition-shadow hover:shadow-md"
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
                      <> &middot; from {cheapestIn.get(g.peerGroup)!.toFixed(2)}%</>
                    )}
                  </p>
                </Link>
              ))}
            </div>

          </div>

          <aside className="order-3 lg:sticky lg:top-[76px]">
            <h3 className={eyebrow} style={{ color: C.gold }}>
              Tools
            </h3>
            <ul className="mt-3 space-y-2.5">
              {INVEST_TOOLS.map(([href, title, note]) => (
                <ToolCard
                  key={href}
                  href={href}
                  title={title}
                  note={note}
                  edge={
                    href.includes("commodity")
                      ? C.gold
                      : href.includes("shares") || href.includes("brokers")
                        ? C.teal
                        : C.deep
                  }
                />
              ))}
            </ul>

            {/*
              What the site cannot show, and why. A visitor who wonders where
              the other sixty-seven funds are should find the answer beside
              the tools rather than having to look for it.
            */}
            <section
              className="mt-6 rounded-2xl p-4"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <p className="text-[12.5px] font-bold">8 funds of 75, in full</p>
              <p
                className="mt-1.5 text-[11.5px] leading-relaxed"
                style={{ color: C.muted }}
              >
                Eight Ghanaian funds publish enough to show what they charge
                and what they returned. Those are compared here.
                <br />
                <br />
                The other 67 are listed with the fields blank. We are in
                contact with providers to close the gaps, and publish whatever
                they send, cited and dated — an empty row is more use to you
                than a number we made up.
              </p>
              <p className="mt-2 text-[12px]">
                <Link
                  href="/funds"
                  className="font-semibold underline underline-offset-4"
                  style={{ color: C.deep }}
                >
                  See all 75 &rarr;
                </Link>
              </p>
            </section>
          </aside>
        </div>

        {/*
          Below the columns, at full width.

          These were in the centre, which made it much taller than the side
          columns and left a long gap either side of everything low on the
          page. Chasing equal heights by adding content is padding; taking the
          tall parts out is the structural fix — and the findings row wanted
          the width anyway, since three cards squeezed into a narrow middle
          were never going to read well.
        */}
        {/*
          Three figures nobody else publishes.

          Each survives the outreach succeeding, which is the test for a
          home page: a gold premium is a price, the index is a market fact,
          and the fee gap comes from the regulator. An earlier version led
          with "0 of 24 brokers publish a rate" — true, and wrong the
          moment one replies.
        */}
        <h3 className={`mt-8 ${eyebrow}`} style={{ color: C.gold }}>
          What the numbers show
        </h3>
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
                C.brown,
              ],
            ] as [string, string, string, string][]
          ).map(([href, figure, note, colour]) => (
            <Link
              key={href}
              href={href}
              className="rounded-2xl p-4 transition-shadow hover:shadow-md"
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


        <section
          className="mt-8 rounded-2xl p-5"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h3 className="text-[14px] font-bold">
            Where these figures come from
          </h3>
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
          The newsletter, full width.

          It was in the left column, which made that column the long one and
          simply moved the gap rather than closing it. Three columns holding
          different content will never end level, so the tall things belong
          out here — and a subscribe box in a 260px column was cramped
          anyway.
        */}
        <div className="mt-8">
          <Subscribe source="home" />
        </div>


        <Faq />

        {/* ───────────────────────── BORROWING ───────────────────────── */}
        <div className="mt-14">
          <SectionHead
            label="Borrowing"
            colour={C.brown}
            note="What 22 Ghanaian banks charge for business, personal and corporate credit"
          />

          <div className={grid}>
            <aside className="order-2 lg:sticky lg:top-[76px] lg:order-1">
              <h3 className={eyebrow} style={{ color: C.brown }}>
                Reading
              </h3>
              {borrowArticles.length === 0 ? (
                <p className="mt-3 text-[13px]" style={{ color: C.muted }}>
                  Nothing published yet.
                </p>
              ) : (
                <ul className="mt-3 space-y-2.5">
                  {borrowArticles.map((a) => (
                    <ArticleCard key={a.slug} a={a} edge={C.brown} />
                  ))}
                </ul>
              )}
            </aside>

            <div className="order-1 lg:order-2">
              <section
                className="overflow-hidden rounded-3xl p-6 text-white sm:p-7"
                style={{
                  background: `linear-gradient(135deg, ${C.brownDeep} 0%, ${C.brownLight} 75%)`,
                }}
              >
                <h2
                  className="text-[1.45rem] font-bold leading-tight sm:text-[1.8rem]"
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

                <div className="mt-5 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-[9.5px] uppercase tracking-wider opacity-75">
                      Cheapest
                    </p>
                    <p
                      className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none"
                      style={{ color: C.gold }}
                    >
                      11.03%
                    </p>
                    <p className="mt-1 text-[10px] opacity-70">
                      Standard Chartered
                    </p>
                  </div>
                  <div>
                    <p className="text-[9.5px] uppercase tracking-wider opacity-75">
                      Dearest
                    </p>
                    <p className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none">
                      33.58%
                    </p>
                    <p className="mt-1 text-[10px] opacity-70">Guaranty Trust</p>
                  </div>
                </div>

                {/*
                  Nine combinations, because that is what the data holds —
                  three kinds of credit at one, three and five years, from Bank
                  of Ghana APR returns. /funding already filters on type and
                  term, so each lands on the right comparison rather than the
                  same page nine times.
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

            <aside className="order-3 lg:sticky lg:top-[76px]">
              <h3 className={eyebrow} style={{ color: C.brown }}>
                Tools
              </h3>
              <ul className="mt-3 space-y-2.5">
                {BORROW_TOOLS.map(([href, title, note]) => (
                  <ToolCard
                    key={href}
                    href={href}
                    title={title}
                    note={note}
                    edge={C.brown}
                  />
                ))}
              </ul>

              {/*
                The ask, at the foot of the page. Most of what is missing from
                this site is missing because nobody publishes it, and a
                provider landing here should find the invitation without
                hunting.
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

          <section
            className="mt-6 rounded-2xl p-5"
            style={{ background: C.card, border: `1px solid ${C.rule}` }}
          >
            <h3 className="text-[14px] font-bold">
              Where the lending figures come from
            </h3>
            <p
              className="mt-2 text-[13px] leading-relaxed"
              style={{ color: C.muted }}
            >
              Bank of Ghana&rsquo;s Annual Percentage Rates and Average
              Interest Rates returns, which every bank is required to file.
              They show what a loan costs once fees are counted — not the
              interest rate on the poster. Three of the twenty-two banks
              mention a rate on their own website.
            </p>
          </section>
        </div>
      </div>

      <Footer />
    </main>
  );
}
