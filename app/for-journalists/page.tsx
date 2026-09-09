import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import { BRAND } from "@/lib/brand";
import {
  getTbillRates,
  getLatestInflation,
  getLendingSpread,
} from "@/lib/data/funds";

/**
 * app/for-journalists/page.tsx
 *
 * WHY THIS PAGE EXISTS
 * A reporter writing about Ghanaian lending rates needs a figure and a source
 * by four o'clock. Without this page they would have to find us, work out what
 * we hold, and email to ask whether they may use it. Most would not bother,
 * and they would be right not to.
 *
 * This removes every step. Here are the numbers, here is where each came from,
 * here is the date, use them.
 *
 * WHAT IT DELIBERATELY IS NOT
 * A media kit. No logos, no boilerplate, no founder photograph, no request to
 * be covered. A journalist arriving here wants a number, not a company. If we
 * are useful once we will be asked again, and that is the whole strategy.
 *
 * WHY THE FIGURES ARE LIVE
 * A press page with hard-coded numbers is wrong within a week and worse than
 * useless — somebody quotes it and we have misled a newspaper. These read from
 * the same database as every other page, so they are current or they are
 * absent.
 */

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

export const metadata = {
  title: "For journalists — Ghanaian market figures, free to use",
  description:
    "Current Ghanaian lending rates, Treasury bill yields, inflation and fund charges, with sources and dates. Free to quote, no permission needed, no credit required.",
};

/**
 * Findings rather than figures — each is something we established that is not
 * published anywhere else, stated in one line a reporter could quote.
 */
const FINDINGS: { claim: string; detail: string; href: string }[] = [
  {
    claim: "A Ghanaian SME can pay three times as much for the same loan",
    detail:
      "11.03% at the cheapest of 22 banks against 33.58% at the dearest, for a one-year facility in the same month. About GH₵22,550 a year of difference on GH₵100,000. From Bank of Ghana's own APR returns.",
    href: "/funding",
  },
  {
    claim: "Bank fees are falling, three times faster for large borrowers",
    detail:
      "Across four Bank of Ghana reports spanning twenty months, the gap between the advertised rate and the all-in APR narrowed 49% for corporate borrowers and 16% for SMEs. The disparity between the largest and smallest borrowers widened while the picture improved for both.",
    href: "/insights/bank-fees-falling-not-equally",
  },
  {
    claim: "Not one of Ghana's 24 licensed stockbrokers publishes a commission rate",
    detail:
      "We visited every website in August 2026, then re-checked platform subdomains and fee pages in September after a broker pointed out we had looked in the wrong place. A Ghanaian cannot establish the cost of buying a share before opening an account with somebody.",
    href: "/brokers",
  },
  {
    claim: "The alternative to a bank costs more, not less",
    detail:
      "Of 26 licensed savings and loans companies, two publish a lending rate. The one unambiguous figure is 42% on a public sector loan, plus 2% processing and 1% monitoring — eight points above the dearest of the 22 banks.",
    href: "/funding#savings-loans",
  },
  {
    claim: "Qualifying for the cheap money was decided months ago",
    detail:
      "Banks that publish criteria require six months of banking history with them before a business loan is available at all. Shopping around at the point of need does not work, because the qualifying history cannot be manufactured.",
    href: "/insights/loan-you-qualify-for-was-decided-months-ago",
  },
  {
    claim: "Bank of Ghana publishes the APR report monthly and keeps no archive",
    detail:
      "Only the current notice is on their site. We checked eight earlier months and found none. Any analysis across time is possible only for somebody who was collecting at the time.",
    href: "/methodology",
  },
  {
    claim: "Two of 106 Ghanaian funds say what a non-resident needs",
    detail:
      "Across 106 collective investment schemes, 24 brokers and 26 savings and loans companies, two published positions on whether somebody living abroad can open an account. Ghanaians sent home US$7.8bn in 2025.",
    href: "/investing-from-abroad",
  },
];

export const revalidate = 3600;

export default async function ForJournalistsPage() {
  const [rates, inflation, spread] = await Promise.all([
    getTbillRates(),
    getLatestInflation(),
    getLendingSpread(),
  ]);

  const fmtPct = (v: number | null) => (v === null ? "—" : `${v.toFixed(2)}%`);

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div className="mx-auto max-w-3xl px-5 py-10 sm:px-8 sm:py-12">
        <p
          className="text-[11px] font-semibold uppercase tracking-[0.16em]"
          style={{ color: C.gold }}
        >
          For journalists
        </p>
        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.1] sm:text-[2.4rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.02em",
          }}
        >
          Use anything on this page
        </h1>
        <p
          className="mt-5 text-[16.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          Every figure we hold is free to quote. No permission, no embargo, no
          credit required, and no need to tell us. If it is useful, take it.
        </p>

        {/* The offer, stated once and without conditions. */}
        <div
          className="mt-6 rounded-2xl p-5"
          style={{ background: "#FFF8EC", border: `1px solid ${C.gold}` }}
        >
          <p className="text-[14px] leading-relaxed">
            <strong>On a deadline?</strong> Write to{" "}
            <a
              href={`mailto:${BRAND.dataEmail}`}
              className="font-semibold underline underline-offset-4"
              style={{ color: C.deep }}
            >
              {BRAND.dataEmail}
            </a>{" "}
            and we will send whatever we hold — a spreadsheet, the underlying
            regulator PDFs, or a figure checked against source — the same day
            where we possibly can. There is no charge and nothing wanted in
            return.
          </p>
        </div>

        <hr
          className="mt-8 w-14"
          style={{ borderColor: C.gold, borderTopWidth: "3px" }}
        />

        {/* Live figures. Hard-coding these would make the page wrong within a
            week, and a journalist quoting a stale number is worse than one who
            never found us. */}
        <h2
          className="mt-10 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Current figures
        </h2>
        <p className="mt-2 text-[14px]" style={{ color: C.muted }}>
          Read live from our database, so this page is never out of date. Each
          carries the date it was last true.
        </p>

        <div className="mt-4 space-y-2">
          {spread && (
            <div
              className="rounded-2xl p-4"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em]" style={{ color: C.muted }}>
                One-year SME loan, all-in APR
              </p>
              <p className="mt-1 text-[1.4rem] font-bold tabular-nums">
                {fmtPct(spread.minPct)} – {fmtPct(spread.maxPct)}
              </p>
              <p className="mt-1 text-[12.5px]" style={{ color: C.muted }}>
                {spread.cheapest} to {spread.dearest}, across {spread.banks}{" "}
                banks. Bank of Ghana APR returns
                {spread.asOf ? `, ${spread.asOf}` : ""}.
              </p>
            </div>
          )}

          {rates.map((r) => (
            <div
              key={r.days}
              className="rounded-2xl p-4"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em]" style={{ color: C.muted }}>
                {r.days}-day Treasury bill
              </p>
              <p className="mt-1 text-[1.4rem] font-bold tabular-nums">
                {r.ratePct.toFixed(2)}%
              </p>
              <p className="mt-1 text-[12.5px]" style={{ color: C.muted }}>
                Bank of Ghana auction{r.asOf ? `, ${r.asOf}` : ""}
              </p>
            </div>
          ))}

          {inflation !== null && (
            <div
              className="rounded-2xl p-4"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em]" style={{ color: C.muted }}>
                Inflation, year on year
              </p>
              <p className="mt-1 text-[1.4rem] font-bold tabular-nums">
                {inflation.toFixed(1)}%
              </p>
              <p className="mt-1 text-[12.5px]" style={{ color: C.muted }}>
                Ghana Statistical Service. We hold the monthly series from June
                2025 and the annual index from 1964.
              </p>
            </div>
          )}
        </div>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Findings you will not get elsewhere
        </h2>
        <p className="mt-2 text-[14px]" style={{ color: C.muted }}>
          Each of these came out of assembling regulator filings and provider
          disclosures that nobody had put together. Every one is checkable
          against its source.
        </p>

        <div className="mt-4 space-y-3">
          {FINDINGS.map(({ claim, detail, href }) => (
            <section
              key={claim}
              className="overflow-hidden rounded-2xl"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <div className="flex">
                <span
                  className="w-1 shrink-0"
                  style={{ background: C.deep }}
                  aria-hidden="true"
                />
                <div className="flex-1 p-5">
                  <p className="text-[15px] font-bold">{claim}</p>
                  <p
                    className="mt-2 text-[14px] leading-relaxed"
                    style={{ color: C.muted }}
                  >
                    {detail}
                  </p>
                  <p className="mt-2.5 text-[13px]">
                    <Link
                      href={href}
                      className="font-semibold underline underline-offset-4"
                      style={{ color: C.deep }}
                    >
                      The underlying data &rarr;
                    </Link>
                  </p>
                </div>
              </div>
            </section>
          ))}
        </div>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What we will not do
        </h2>
        <div className="mt-4 space-y-3 text-[15px] leading-relaxed">
          <p>
            <strong>Give you a figure we cannot source.</strong> If we do not
            hold something we will say so rather than estimate it. That includes
            figures that would make a better story.
          </p>
          <p>
            <strong>Tell you what a rate means for an individual.</strong> Bank
            of Ghana's returns are averages across each bank's whole book, and
            the Bank says plainly that a given borrower may be offered something
            different. We publish them as indicative and would ask that you do
            too.
          </p>
          <p>
            <strong>Ask for anything.</strong> No credit, no link, no sight of
            the piece before publication. If our figures are useful, use them.
          </p>
        </div>

        <section
          className="mt-10 rounded-2xl p-5"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2 className="text-[14px] font-bold">How to describe us, if you need to</h2>
          <p
            className="mt-2 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            Cedafin is a Ghanaian financial comparison site. It publishes what
            investment and credit products cost, using figures the providers and
            regulators publish themselves, each shown with the date it was true.
            It is not licensed by the Securities and Exchange Commission of
            Ghana, gives no investment advice, holds no client money, and no
            provider can pay to appear or to rank.
          </p>
          <p className="mt-3 text-[13px]">
            <Link
              href="/methodology"
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              How we source every figure &rarr;
            </Link>
          </p>
        </section>

        <p className="mt-8 text-[13px]" style={{ color: C.muted }}>
          Anything unclear, or a figure you need that is not here —{" "}
          <a
            href={`mailto:${BRAND.dataEmail}`}
            className="font-semibold underline underline-offset-4"
            style={{ color: C.deep }}
          >
            {BRAND.dataEmail}
          </a>
        </p>
      </div>

      <Footer />
    </main>
  );
}
