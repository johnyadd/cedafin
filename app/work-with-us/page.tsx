import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import { BRAND } from "@/lib/brand";

/**
 * app/work-with-us/page.tsx — the consultancy offer.
 *
 * WHY THIS PAGE EXISTS AND WHY IT IS NOT AN EMAIL
 * We have written to twenty-four brokers and every fund manager we can reach,
 * asking for their data so a public comparison can be accurate. If that
 * correspondence turned into a sales approach, every one of those emails would
 * be reread as lead generation, and the data outreach is worth more than any
 * single consulting engagement.
 *
 * So this sits on the site and is found rather than sent. Somebody who reads
 * the broker analysis or the APR work and thinks "we need that internally" has
 * somewhere to go. Nobody is pitched.
 *
 * WHY THE EVIDENCE IS UNUSUAL
 * Most consultancy pages assert capability. This one can point at a running
 * system: the extractors, the comparisons, the errors caught, the corrections
 * published. A prospect can verify every claim by clicking.
 *
 * WHAT IT DELIBERATELY DOES NOT SAY
 * No day rates, no packages, no "trusted by" logos we have not earned. The
 * work described is work that has demonstrably been done, and the invitation
 * is to a conversation rather than a purchase.
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
  title: "Financial data extraction and analysis — Ghana",
  description:
    "Turning documents nobody can query into figures you can act on. Regulatory filings, factsheets, market reports. Built and demonstrated on cedafin.com.",
};

/** Each links to the thing itself, because assertion is cheap. */
const EVIDENCE: { claim: string; detail: string; href: string; label: string }[] =
  [
    {
      claim: "Extraction from documents that were never meant to be queried",
      detail:
        "Fifteen months of Ghana Stock Exchange monthly reports, parsed into a price history for all 39 listed companies. Bank of Ghana tender results and daily gold circulars, running on a schedule. Fund factsheets from every manager who publishes one.",
      href: "/shares",
      label: "39 companies, with price history",
    },
    {
      claim: "Comparable figures from filings that resist comparison",
      detail:
        "Bank of Ghana requires every bank to report an annual percentage rate. The figures sit in returns few borrowers ever see. Assembled across 22 banks, three credit types and three terms, the spread turns out to be 22.5 percentage points on the same one-year loan.",
      href: "/funding",
      label: "22 banks, what they actually charge",
    },
    {
      claim: "Analysis that finds what the data was hiding",
      detail:
        "One firm averages 52.7% of the value traded on the Ghana Stock Exchange, swinging between 20% and 79% month to month. One bank advertises 13.70% and reports a maximum of 23.42%. Neither figure is published anywhere; both come out of the filings once assembled.",
      href: "/insights/advertised-rate-against-what-you-pay",
      label: "The gap between advertised and actual",
    },
    {
      claim: "Errors caught, including our own",
      detail:
        "A published return that annualised an eleven-month window. A sector heading that filed a bank under Education. A claim about dividends that a fund manager corrected. Each found, fixed and recorded — because a pipeline that cannot catch its own mistakes is not finished.",
      href: "/methodology",
      label: "How we source every figure",
    },
  ];

const WORK: { title: string; body: string }[] = [
  {
    title: "You have data you cannot use",
    body: "Factsheet archives, regulatory returns, monthly reports, spreadsheets going back years. Everything is there and nothing is queryable, so questions that should take a minute take a week — or never get asked. This is the most common shape of the problem and the most tractable.",
  },
  {
    title: "You need to know where you stand",
    body: "What your charges look like against the market, what your competitors publish and what they do not, how a figure has moved over time. Assembled from the same public filings everyone can see and almost nobody reads.",
  },
  {
    title: "You need something built that keeps running",
    body: "Not a report that is stale in a month, but an extractor that runs on a schedule, checks itself, and tells you when a source changes shape. The pipeline behind this site is that, and it survives its sources being redesigned.",
  },
];

export default function WorkWithUsPage() {
  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div className="mx-auto max-w-3xl px-5 py-10 sm:px-8 sm:py-14">
        <p
          className="text-[11px] font-semibold uppercase tracking-[0.16em]"
          style={{ color: C.gold }}
        >
          Consulting
        </p>
        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.1] sm:text-[2.5rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.02em",
          }}
        >
          Everything on this site came out of documents nobody could query
        </h1>
        <p
          className="mt-5 text-[17px] leading-relaxed"
          style={{ color: C.muted }}
        >
          PDFs, regulatory filings, monthly reports, factsheets. Extracted,
          checked, dated and made comparable. If your organisation has data in
          that state — and most do — this is the same work.
        </p>

        <hr
          className="mt-8 w-14"
          style={{ borderColor: C.gold, borderTopWidth: "3px" }}
        />

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What this looks like in practice
        </h2>
        <div className="mt-5 space-y-6">
          {WORK.map(({ title, body }) => (
            <div key={title}>
              <p className="text-[15.5px] font-bold">{title}</p>
              <p
                className="mt-1.5 text-[15px] leading-relaxed"
                style={{ color: C.muted }}
              >
                {body}
              </p>
            </div>
          ))}
        </div>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          The evidence is the site
        </h2>
        <p className="mt-3 text-[15px] leading-relaxed" style={{ color: C.muted }}>
          Most pages like this assert a capability. Every claim below links to
          the thing itself, so you can check rather than take it on trust.
        </p>

        <div className="mt-5 space-y-3">
          {EVIDENCE.map(({ claim, detail, href, label }) => (
            <section
              key={claim}
              className="rounded-2xl p-5"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <p className="text-[15px] font-bold">{claim}</p>
              <p
                className="mt-2 text-[14px] leading-relaxed"
                style={{ color: C.muted }}
              >
                {detail}
              </p>
              <p className="mt-3 text-[13px]">
                <Link
                  href={href}
                  className="font-semibold underline underline-offset-4"
                  style={{ color: C.deep }}
                >
                  {label} &rarr;
                </Link>
              </p>
            </section>
          ))}
        </div>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Who is behind it
        </h2>
        <p className="mt-3 text-[15px] leading-relaxed">
          John Yaw Addae — a background in financial planning and analysis and
          in data engineering, and an MBA in finance. This site is built and
          maintained single-handed, which is either a recommendation or a
          warning depending on what you need.
        </p>

        {/*
          The separation matters. Providers we have written to for data should
          not wonder whether the request was really a sales approach.
        */}
        <section
          className="mt-8 rounded-2xl p-5"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h3 className="text-[14px] font-bold">
            If we have written to you about your data
          </h3>
          <p
            className="mt-2 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            That request stands on its own. We publish what providers send us,
            cited and dated, at no cost and with no expectation of anything in
            return — and we would do so whether or not this page existed. The
            two things are separate and will stay that way.
          </p>
        </section>

        <section
          className="mt-8 overflow-hidden rounded-2xl p-6 text-white"
          style={{
            background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 72%)`,
          }}
        >
          <h2
            className="text-[1.3rem] font-bold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            If any of that sounds like your problem
          </h2>
          <p className="mt-3 text-[14.5px] leading-relaxed opacity-90">
            Tell us what you are sitting on and what you wish you could ask of
            it. If it is not something we can help with we will say so — and if
            it is, the first conversation is about whether the answer is worth
            having, not about a proposal.
          </p>
          <p className="mt-4 text-[15px] font-bold">
            <a
              href={`mailto:${BRAND.enquiriesEmail}?subject=Data%20work`}
              className="underline underline-offset-4"
              style={{ color: C.gold }}
            >
              {BRAND.enquiriesEmail}
            </a>
          </p>
        </section>

        <p className="mt-8 text-[13px]">
          <Link
            href="/"
            className="underline underline-offset-4"
            style={{ color: C.deep }}
          >
            &larr; Back to the comparisons
          </Link>
        </p>
      </div>

      <Footer />
    </main>
  );
}
