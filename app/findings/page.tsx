import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import { BRAND } from "@/lib/brand";

/**
 * app/findings/page.tsx — everything we have established, in one place.
 *
 * WHY
 * The findings are scattered across a dozen pages and two dozen articles. A
 * journalist, a researcher or anybody deciding whether this site is worth
 * their attention has no way to see them together.
 *
 * WHAT IT IS FOR, three things at once: the page an editor gets pointed at,
 * the source for anything we ever post anywhere, and the answer to "what have
 * you actually found".
 *
 * WHAT IT MUST NOT BECOME
 * A marketing page. "Cedafin uncovers the truth about Ghanaian finance" is a
 * claim and claims invite scepticism. "11.03% at one bank and 33.58% at
 * another, same month, same facility" is a fact, and a reader can check it.
 *
 * So: no adjectives, no superlatives, no "shocking" or "revealed". Every entry
 * is a number, where it came from, and a link to the working. If a finding
 * cannot survive being stated flatly it should not be on the page.
 *
 * AND EVERY ONE IS FREE TO USE. That is the point — a finding nobody repeats
 * is a finding that did not travel.
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
  good: "#0E8F62",
  bg: "#F2F6F9",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
};

export const metadata = {
  title: "What we have found — Ghanaian finance, with the evidence",
  description:
    "Every checkable finding from Cedafin's own data: what banks charge, what providers publish, what the market actually looks like. Free to quote, with the working behind each one.",
};

type Finding = {
  /** The line somebody could quote. Number first where possible. */
  claim: string;
  /** Where it came from, plainly. */
  source: string;
  /** Why it matters to somebody with money to place or borrow. */
  why?: string;
  href: string;
};

const GROUPS: { heading: string; intro: string; findings: Finding[] }[] = [
  {
    heading: "What borrowing costs",
    intro:
      "From Bank of Ghana's Annual Percentage Rate returns, which every bank must file and almost nobody reads.",
    findings: [
      {
        claim:
          "The same one-year SME loan costs 11.03% at one Ghanaian bank and 33.58% at another",
        source: "Bank of Ghana APR returns, May 2026, all 22 banks",
        why: "About GH₵22,550 a year of difference on GH₵100,000 — for the same money, over the same term, from banks the same regulator licenses.",
        href: "/funding",
      },
      {
        claim:
          "One bank advertises 13.70% and reports charging 23.42% once fees are counted",
        source: "Bank of Ghana APR returns, May 2026",
        why: "The widest gap of the 22. The fee categories the Bank publishes account for 4.21 of those 9.72 points; the rest is not explained by any public source.",
        href: "/insights/advertised-rate-against-what-you-pay",
      },
      {
        claim:
          "More than half of one bank's fee gap is not explained by any public source",
        source: "Bank of Ghana APR returns, May 2026",
        why: "The Bank publishes fee categories alongside the APR. For the bank with the widest gap those come to 4.21 percentage points against a gap of 9.72 — so a borrower cannot find out what the remaining 5.51 points are for, and neither can we.",
        href: "/insights/advertised-rate-against-what-you-pay",
      },
      {
        claim:
          "Bank fees are falling three times faster for large borrowers than for small ones",
        source:
          "Four Bank of Ghana returns spanning twenty months — three of which the Bank no longer publishes",
        why: "Corporate fee load down 49%, small business down 16%. The gap between the largest and smallest borrowers widened while the picture improved for both.",
        href: "/insights/bank-fees-falling-not-equally",
      },
      {
        claim:
          "The banks that publish lending criteria require six months of their own account history first",
        source: "Published criteria from the banks that state any",
        why: "Shopping around at the point of need does not work — by the time a business needs money it cannot manufacture six months of turnover through a bank it has never used.",
        href: "/insights/loan-you-qualify-for-was-decided-months-ago",
      },
      {
        claim:
          "Nobody in Ghana publishes what a mortgage costs — including the only licensed mortgage company",
        source:
          "Five institutions' own websites and the Bank of Ghana Mortgage Finance register, September 2026",
        why:
          "Bank of Ghana licenses a category called Mortgage Finance. It has one member, NorthStar Home Finance, and they publish four service lines and no price — no rate, no minimum, no loan-to-value, no term. Absa publishes terms and no rate; Stanbic seven products, four currencies and no rate; Fidelity no rate; GCB no mortgage product. The single exception is Republic, which publishes 18% a year for individuals, 23% for businesses, 13.5% under the government scheme and 11.5% in dollars — all four on their mortgage calculator, and none on the page describing the mortgage.",
        href: "/lenders/republic-bank-ghana",
      },
      {
        claim:
          "A savings and loans company publishes 42% on a public sector loan — eight points above the dearest bank",
        source: "Adehyeman Savings and Loans' own website, September 2026",
        why: "A business refused by a bank may assume the alternative is gentler. On the only clear published figure, it costs materially more.",
        href: "/funding#savings-loans",
      },
    ],
  },
  {
    heading: "What providers do not tell you",
    intro:
      "Established by going to every licensed firm on the regulators' registers and recording what each states. The absences are dated, because an absence only counts if somebody looked.",
    findings: [
      {
        claim:
          "Not one of Ghana's 24 licensed stockbrokers publishes a commission rate",
        source:
          "Every dealing member's website, checked August and September 2026",
        why: "Comparing what brokers charge means contacting them one at a time and asking. Nothing is published, so there is nothing to compare before you start.",
        href: "/brokers",
      },
      {
        claim: "Six of 50 Ghanaian fund managers publish what they charge",
        source: "Provider material, against the SEC licensee register",
        why: "Two funds holding the same instruments can differ by more than two percentage points a year — most of the difference between them over a decade.",
        href: "/what-gets-published",
      },
      {
        claim:
          "24 of Ghana's 26 licensed savings and loans companies publish no lending rate at all",
        source: "Bank of Ghana's register, every website visited September 2026",
        why: "There is no APR table for these institutions, so a borrower turned down by a bank cannot establish what the alternative costs before committing.",
        href: "/funding#savings-loans",
      },
      {
        claim:
          "Six of 97 Ghanaian providers say anything about whether somebody living abroad can open an account",
        source: "Provider material across funds, brokers and banks",
        why: "Ghanaians abroad sent home US$7.8bn in 2025. Almost none of them can establish, before committing money, whether a product is open to them.",
        href: "/investing-from-abroad",
      },
      {
        claim:
          "Six of 24 broker contact details on the regulator's own register did not reach the firm",
        source:
          "Writing to every licensed dealing member, August and September 2026",
        why: "An investor using the details the regulator publishes meets the same wall, without knowing why.",
        href: "/insights/ghanaian-brokers-publish-nothing",
      },
    ],
  },
  {
    heading: "What the market actually looks like",
    intro:
      "From the Ghana Stock Exchange's own monthly reports, assembled into a series the Exchange does not publish.",
    findings: [
      {
        claim:
          "One broker averages 54% of all value traded — and swings between 20% and 79% month to month",
        source: "Eighteen Ghana Stock Exchange monthly reports, Feb 2025 to Jul 2026",
        why: "A fifty-nine point swing with no direction is a fact about how thin the exchange is, not about how dominant any firm is. A few large trades decide who leads in any month.",
        href: "/brokers",
      },
      {
        claim:
          "The index rose 76% in the year to July 2026 while volume fell 72%",
        source: "Ghana Stock Exchange monthly reports",
        why: "A gain in a market that quiet is not necessarily one you can sell into.",
        href: "/shares",
      },
      {
        claim:
          "The smallest Ghana Gold Coin costs 7.75% more than the gold inside it",
        source:
          "Bank of Ghana daily coin circulars against LBMA reference prices",
        why: "Gold is recommended to ordinary savers as protection, and the cheapest way in carries the largest premium.",
        href: "/compare/commodity-GHS",
      },
      {
        claim:
          "The 91-day Treasury bill pays almost exactly the inflation rate",
        source: "Bank of Ghana auction results against Ghana Statistical Service CPI",
        why: "The safest Ghanaian product currently returns close to nothing in real terms. Every other return on this site is shown against the same benchmark.",
        href: "/treasury-bill-calculator",
      },
    ],
  },
  {
    heading: "What it takes to start",
    intro:
      "Minimums and access terms, from the providers that state them.",
    findings: [
      {
        claim: "The lowest published minimum in Ghana is GH₵1",
        source: "IC's own material, September 2026",
        why: "One cedi opens and maintains a licensed money market fund, subscribed online. Ecobank's TBill4All sells government Treasury bills from GH₵5 through mobile money with no bank account.",
        href: "/insights/how-to-start-investing-in-ghana",
      },
      {
        claim:
          "One provider publishes the whole route from abroad — and only one",
        source: "IC's own FAQ, September 2026",
        why: "Passport accepted as identification, account activated within 24 hours, funded by card or mobile money, withdrawn online. Nobody else we have checked publishes all of it.",
        href: "/investing-from-abroad",
      },
      {
        claim:
          "Only one Ghanaian provider mentions the cost of the paperwork for a non-resident",
        source: "EDC Stockbrokers' trading portal, September 2026",
        why: "Documents notarised by a foreign authority. A notary outside Ghana charges per document — which may cost more than somebody intends to invest.",
        href: "/investing-from-abroad",
      },
    ],
  },
  {
    heading: "What the institutions do not keep",
    intro: "Found by trying to look something up and failing.",
    findings: [
      {
        claim:
          "Bank of Ghana publishes its lending rate return monthly and keeps no accessible archive",
        source: "Eight earlier months checked; no published notice for any",
        why: "So nobody outside the Bank can say whether borrowing is getting cheaper — unless they happened to be collecting at the time.",
        href: "/the-archive",
      },
      {
        claim:
          "A fund cut its charge from 2.65% to 2.25% — provable only from documents we kept",
        source: "Two factsheets, May and June 2026",
        why: "Fund managers replace a factsheet rather than versioning it. Their own site shows the figure that is true today and no trace of what it was.",
        href: "/the-archive",
      },
    ],
  },
];

export const revalidate = 3600;

export default function FindingsPage() {
  const total = GROUPS.reduce((n, g) => n + g.findings.length, 0);

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
          {total} findings, each with its working
        </p>
        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.1] sm:text-[2.4rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.02em",
          }}
        >
          What we have found
        </h1>
        <p
          className="mt-5 text-[16.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          None of this was hidden. All of it came from documents Ghanaian
          institutions published themselves — and none of it was visible until
          somebody put the documents side by side.
        </p>

        <div
          className="mt-6 rounded-2xl p-5"
          style={{ background: "#FFF8EC", border: `1px solid ${C.gold}` }}
        >
          <p className="text-[14px] leading-relaxed">
            <strong>Use any of it.</strong> Quote it, republish it, put it in an
            article or a deck. No permission needed, no credit required, no need
            to tell us. Every line links to the working so you can check it
            before you repeat it — which you should.
          </p>
        </div>

        {GROUPS.map((g) => (
          <section key={g.heading} className="mt-12">
            <h2
              className="text-[1.5rem] font-bold"
              style={{ fontFamily: "var(--font-display)" }}
            >
              {g.heading}
            </h2>
            <p
              className="mt-2 text-[14px] leading-relaxed"
              style={{ color: C.muted }}
            >
              {g.intro}
            </p>

            <div className="mt-4 space-y-3">
              {g.findings.map((f) => (
                <article
                  key={f.claim}
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
                      <p className="text-[15px] font-bold leading-snug">
                        {f.claim}
                      </p>
                      {f.why && (
                        <p
                          className="mt-2 text-[13.5px] leading-relaxed"
                          style={{ color: C.muted }}
                        >
                          {f.why}
                        </p>
                      )}
                      <p
                        className="mt-2.5 text-[12px]"
                        style={{ color: C.muted }}
                      >
                        {f.source}
                      </p>
                      <p className="mt-2 text-[13px]">
                        <Link
                          href={f.href}
                          className="font-semibold underline underline-offset-4"
                          style={{ color: C.deep }}
                        >
                          The working &rarr;
                        </Link>
                      </p>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ))}

        <section
          className="mt-12 rounded-2xl p-5"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2 className="text-[14.5px] font-bold">
            What is not on this page
          </h2>
          <p
            className="mt-2 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            Anything we cannot show. Several things we suspect are true about
            Ghanaian finance are not here, because suspecting is not
            establishing — and a page of findings is only worth reading if
            everything on it survives being checked.
          </p>
          <p
            className="mt-2.5 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            Where a finding turns out to be wrong we correct it and say so.
            That has happened, and it will again.
          </p>
          <p className="mt-3 text-[13px]">
            <Link
              href="/methodology"
              className="font-semibold underline underline-offset-4"
              style={{ color: C.deep }}
            >
              How we source every figure &rarr;
            </Link>
            {" · "}
            <a
              href={`mailto:${BRAND.dataEmail}`}
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              {BRAND.dataEmail}
            </a>
          </p>
        </section>

        <p className="mt-8 text-[12.5px]" style={{ color: C.muted }}>
          {BRAND.legalStatus}
        </p>
      </div>

      <Footer />
    </main>
  );
}
