import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import { BRAND } from "@/lib/brand";

/**
 * app/work-with-us/page.tsx — the consultancy offer.
 *
 * WHY THIS PAGE IS FOUND RATHER THAN SENT
 * We have written to twenty-four brokers and every fund manager we can reach,
 * asking for their data so a public comparison can be accurate. If that
 * correspondence became a sales approach, every one of those emails would be
 * reread as lead generation. So this sits on the site. Nobody is pitched.
 *
 * WHY THE EVIDENCE SECTION DESCRIBES OUTPUT AND NOT METHOD
 * An earlier version named the exact documents, institutions and frequencies
 * behind each extractor. That is a recipe, and there is no reason to publish
 * one. The claims and the links are unchanged, so a prospect still verifies
 * everything by clicking; what went is how it was done.
 *
 * WHY NO RATES OR PACKAGES
 * The work varies too much for a price list to be honest, and a day rate on a
 * page invites comparison on the wrong axis. The invitation is to a
 * conversation about whether the answer is worth having.
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
  title: "Financial analysis, modelling and data consulting",
  description:
    "Fractional CFO work, financial modelling, data extraction and pipelines, market analysis and reporting. Demonstrated on cedafin.com and delivered remotely or on site.",
};

/**
 * The services, ordered by how directly this site evidences them. Each says
 * what it is, who tends to need it, and what arrives at the end — because
 * "financial consulting" as a phrase tells a buyer nothing.
 */
const SERVICES: {
  title: string;
  who: string;
  body: string;
  deliverable: string;
}[] = [
  {
    title: "Data extraction and pipelines",
    who: "Anyone with figures locked in documents",
    body:
      "Reports, filings, factsheets, statements and spreadsheets that hold everything you need and answer nothing you ask. Turned into a structured series that can be queried, compared and kept current — with the checks that catch it when a source changes shape.",
    deliverable:
      "A running extractor, a documented schema, and the data in a form your own tools can read.",
  },
  {
    title: "Financial modelling and forecasting",
    who: "Founders raising, boards deciding, finance teams planning",
    body:
      "Three-statement models, scenario and sensitivity analysis, cash flow forecasting, unit economics, budgets and reforecasts. Built to be understood and changed by the people who own them rather than admired and abandoned.",
    deliverable:
      "A model you can drive yourself, with the assumptions visible and the logic traceable.",
  },
  {
    title: "Fractional CFO and FP&A",
    who: "Businesses that need the function, not the salary",
    body:
      "Management reporting, budgeting and variance analysis, cash management, pricing and margin work, board packs, and the finance discipline that turns bookkeeping into decisions. Ongoing or for a defined stretch.",
    deliverable:
      "A monthly rhythm — numbers that arrive on time, in a form that supports a decision.",
  },
  {
    title: "Market and competitive analysis",
    who: "Anyone who needs to know where they stand",
    body:
      "What competitors charge, what they publish and what they conspicuously do not, how a market has moved, where the outliers are. Assembled from public filings that everyone can see and almost nobody reads.",
    deliverable:
      "A findings document with every figure sourced and dated, and the working shown.",
  },
  {
    title: "Reporting and dashboards",
    who: "Teams drowning in data and short of answers",
    body:
      "The layer between a warehouse and a decision. Metrics defined so they mean the same thing to everyone, refreshed automatically, and presented so the exception is visible without hunting for it.",
    deliverable:
      "Dashboards that update themselves, and a definition of every metric on them.",
  },
  {
    title: "Getting your data ready for AI",
    who: "Anyone whose AI project stalled on the data",
    body:
      "Industry research is consistent that models are not the bottleneck — governance, lineage and clean pipelines are, and most organisations discover this after the pilot. Structured, documented, reproducible data with provenance on every figure: where it came from, when it was true, how it was derived. Plus the checks that catch an error before a model learns from it.",
    deliverable:
      "A dataset a model can be pointed at without inheriting your document problem — sourced, dated, and reproducible from the originals.",
  },
  {
    title: "Data engineering",
    who: "Organisations with sources that will not talk to each other",
    body:
      "Warehouse design, ingestion and transformation, migration between platforms, data quality and reconciliation. Experience across Databricks, SQL Server and SSIS, and the pragmatic end of the stack where most real work happens.",
    deliverable:
      "Pipelines that run unattended, fail loudly rather than silently, and can be handed over.",
  },
];

/** Each links to the thing itself, because assertion is cheap. */
const EVIDENCE: { claim: string; detail: string; href: string; label: string }[] =
  [
    {
      claim: "Extraction from documents that were never meant to be queried",
      detail:
        "Monthly market documents published as prose and tables, turned into a queryable price history for every listed company. Daily and weekly releases from several institutions, extracted on a schedule and reconciled against each other. The result is a series; the inputs were never designed to produce one.",
      href: "/shares",
      label: "39 companies, with price history",
    },
    {
      claim: "Comparable figures from filings that resist comparison",
      detail:
        "Regulatory filings that exist to be filed rather than read. Assembled across 22 institutions, three product types and three terms, they show a spread of 22.5 percentage points on the same one-year facility — a figure nobody publishes because nobody had put the returns side by side.",
      href: "/funding",
      label: "22 banks, what they actually charge",
    },
    {
      claim: "Analysis that finds what the data was hiding",
      detail:
        "A market concentration nobody had measured. A gap of nearly ten percentage points between what one institution advertises and what it reports charging. Neither figure appears in any single document — both emerge only once the series exists, which is the point of building one.",
      href: "/insights/advertised-rate-against-what-you-pay",
      label: "The gap between advertised and actual",
    },
    {
      claim: "Errors caught, including our own",
      detail:
        "A return that annualised a partial window. A classification that mislabelled a major institution. A published claim that a provider corrected. Each found, fixed and recorded — because a pipeline that cannot catch its own mistakes is not finished, and the checks matter more than the extraction.",
      href: "/methodology",
      label: "How we source every figure",
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
          Financial analysis, modelling and data work — for organisations
          sitting on information they cannot use, or decisions they cannot
          evidence. This site is the demonstration; the same work is available
          to you.
        </p>

        <hr
          className="mt-8 w-14"
          style={{ borderColor: C.gold, borderTopWidth: "3px" }}
        />

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What we do
        </h2>
        <p
          className="mt-3 text-[15px] leading-relaxed"
          style={{ color: C.muted }}
        >
          Seven things, and most engagements are one or two of them. Each says
          what arrives at the end, because &ldquo;financial consulting&rdquo; as
          a phrase tells nobody anything.
        </p>

        <div className="mt-5 space-y-3">
          {SERVICES.map(({ title, who, body: text, deliverable }) => (
            <section
              key={title}
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
                  <h3 className="text-[15.5px] font-bold">{title}</h3>
                  <p
                    className="mt-0.5 text-[11.5px] font-semibold uppercase tracking-[0.1em]"
                    style={{ color: C.gold }}
                  >
                    {who}
                  </p>
                  <p
                    className="mt-2.5 text-[14px] leading-relaxed"
                    style={{ color: C.muted }}
                  >
                    {text}
                  </p>
                  <p
                    className="mt-3 border-t pt-2.5 text-[13px] leading-relaxed"
                    style={{ borderColor: C.rule }}
                  >
                    <strong>What you get:</strong>{" "}
                    <span style={{ color: C.muted }}>{deliverable}</span>
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
          How it works
        </h2>
        <div className="mt-4 space-y-4 text-[15px] leading-relaxed">
          <p>
            <strong>Remotely, or on site where it matters.</strong> Most of this
            work is done wherever the data is, which is usually nowhere in
            particular. Clients in Ghana, the United Kingdom and elsewhere are
            equally practical.
          </p>
          <p>
            <strong>Scoped before it is priced.</strong> The first conversation
            establishes whether the answer you want is obtainable and whether it
            is worth what it would cost to get. Sometimes it is not, and saying
            so is part of the service.
          </p>
          <p>
            <strong>Deterministic where it matters.</strong> The extraction
            behind this site uses no language models. For financial figures
            that is deliberate — same input, same output, every time, and a
            wrong number is a bug rather than a plausible-looking guess. Models
            are useful downstream, on data that has already been made
            trustworthy.
          </p>
          <p>
            <strong>Built to be handed over.</strong> A pipeline nobody but its
            author can maintain is a liability. Everything comes documented, in
            tools you already have where possible.
          </p>
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
              href={`mailto:${BRAND.enquiriesEmail}?subject=Consulting%20enquiry`}
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
