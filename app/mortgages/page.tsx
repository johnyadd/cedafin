import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import DataProvenance from "@/components/DataProvenance";
import Footer from "@/components/Footer";
import ShareThis from "@/components/ShareThis";
import { BRAND } from "@/lib/brand";
import { getLending } from "@/lib/data/funds";

/**
 * app/mortgages/page.tsx — what a Ghanaian mortgage costs, and why almost
 * nobody will tell you.
 *
 * WHY THIS IS ONE PAGE AND NOT TWO
 * A comparison page needs rates from several lenders. Ghana has one bank
 * publishing a rate. A disclosure page — here is what nobody tells you —
 * works with exactly that, but leaves somebody who came to compare with
 * nothing to compare.
 *
 * So both, in one page, with the comparison first. The table is very short,
 * and its shortness is the finding.
 *
 * WHAT IS READ FROM THE DATABASE
 * The rates. Republic's four products carry asset_class = mortgage, so this
 * table fills itself the day a second bank publishes. Nothing here needs
 * editing when that happens.
 *
 * WHY THE TERMS ARE PROSE AND NOT A TABLE
 * Each bank publishes a different subset — Absa give loan-to-value and tenor,
 * Stanbic give products and currencies, First National give eligibility. A
 * table across them would be five columns of mostly empty cells, which reads
 * as absence of data rather than difference of disclosure. The cards show
 * what each one actually says.
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
  title: "Ghanaian mortgage rates — one bank of twenty-one publishes one",
  description:
    "Republic Bank publishes 18% a year for individuals and 23% for businesses. No other Ghanaian bank publishes a mortgage rate at all, including the market leader and the country's only licensed mortgage finance company.",
  keywords: [
    "mortgage rates Ghana",
    "home loan Ghana",
    "Ghana mortgage interest rate",
    "buy a house in Ghana",
    "Ghana mortgage for non-residents",
  ],
  openGraph: { images: ["/api/card/lending-spread"] },
};

/** Which banks publish terms, and the order to show them in. */
const TERMS_ORDER = [
  "republic-bank-ghana",
  "first-national-bank-ghana",
  "stanbic-bank-ghana",
  "absa-bank-ghana",
  "fidelity-bank-ghana",
];

const ASK = [
  "Is the rate fixed or variable? Republic's four are fixed; Stanbic describe theirs as variable. Over twenty years that is the difference between a cost you can plan for and one you cannot.",
  "What is the all-in cost? A rate is not a price. Ask for the facility fee, the processing fee, the valuation fee, the legal fee and any annual review charge, as a total.",
  "What deposit do you need, and is the insurance separate? First National's 100% Purchase loan carries an insurance policy of up to 30% of the purchase price — which is not a deposit, and not a loan-to-value ratio.",
  "If you live abroad, in which currency can you borrow? Republic lend dollars to non-residents; Stanbic and First National both offer pounds. Borrowing in the currency you earn removes the exchange risk from the repayment.",
  "What happens if the rate moves? On a variable rate over twenty years, ask what the highest payment could be rather than what today's is.",
];

export const revalidate = 3600;

export default async function MortgagesPage() {
  const all = await getLending();
  const mortgages = all
    .filter((r) => r.category === "mortgage")
    .sort((a, b) => (a.aprPct ?? 99) - (b.aprPct ?? 99));

  const lenders = new Set(mortgages.map((m) => m.provider.slug));

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
          Buying a home in Ghana
        </p>
        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.1] sm:text-[2.4rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.02em",
          }}
        >
          One bank of twenty-one publishes a mortgage rate
        </h1>
        <p
          className="mt-5 text-[16.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          We read every Ghanaian bank&rsquo;s own website looking for the price
          of a home loan. One had it. Here is what they say, what everybody
          else says instead, and what it means for the arithmetic of buying.
        </p>

        {/* The rates. From the database, so a second bank appears here without
            anybody editing this page. */}
        <h2
          className="mt-10 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          The published rates
        </h2>
        {mortgages.length === 0 ? (
          <p className="mt-3 text-[15px]" style={{ color: C.muted }}>
            None currently held.
          </p>
        ) : (
          <>
            <p className="mt-2 text-[13.5px]" style={{ color: C.muted }}>
              All from {lenders.size === 1 ? "one lender" : `${lenders.size} lenders`}
              , read from their own material. Fees are charged on top.
            </p>
            <div className="mt-4 space-y-2">
              {mortgages.map((m) => (
                <div
                  key={m.slug}
                  className="rounded-2xl p-4 sm:p-5"
                  style={{ background: C.card, border: `1px solid ${C.rule}` }}
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <div>
                      <p className="text-[14.5px] font-bold">{m.name}</p>
                      <p className="text-[12px]" style={{ color: C.muted }}>
                        {/* The product name already carries the currency —
                            "Home Purchase Mortgage (USD)" — so there is
                            nothing to add here. */}
                        {m.provider.name}
                      </p>
                    </div>
                    <span
                      className="text-[1.4rem] font-bold tabular-nums"
                      style={{ color: C.deep }}
                    >
                      {m.aprPct !== null ? `${m.aprPct.toFixed(2)}% ` : "— "}
                      <span
                        className="ml-1.5 text-[11px] font-semibold"
                        style={{ color: C.muted }}
                      >
                        a year
                      </span>
                    </span>
                  </div>
                  {m.caveat && (
                    <p
                      className="mt-2 text-[13px] leading-relaxed"
                      style={{ color: C.muted }}
                    >
                      {m.caveat}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

        {/* The absence. This is the actual finding. */}
        <div
          className="mt-8 overflow-hidden rounded-2xl"
          style={{ background: C.card, border: `1px solid ${C.clay}` }}
        >
          <div className="flex">
            <span className="w-1 shrink-0" style={{ background: C.clay }} aria-hidden="true" />
            <div className="flex-1 p-5">
              <p className="text-[15px] font-bold">
                Twenty-one bank websites, one rate
              </p>
              <p
                className="mt-2.5 text-[14px] leading-relaxed"
                style={{ color: C.muted }}
              >
                In September 2026 we read the mortgage and home loan pages of
                every Ghanaian bank whose site we could reach — twenty-one of
                twenty-three, following each site&rsquo;s own navigation rather
                than guessing addresses. One published an interest rate.
              </p>
              <p
                className="mt-2.5 text-[14px] leading-relaxed"
                style={{ color: C.muted }}
              >
                <strong>First National Bank</strong>, who acquired Ghana Home
                Loans and are described in the Ghanaian business press as the
                country&rsquo;s mortgage leaders, publish four home loan
                products and no price for any of them.
              </p>
              <p
                className="mt-2.5 text-[14px] leading-relaxed"
                style={{ color: C.muted }}
              >
                Bank of Ghana also licenses a separate category called Mortgage
                Finance. It has one member,{" "}
                <strong>NorthStar Home Finance</strong>. They publish four
                service lines and no rate, no minimum, no loan-to-value and no
                term.
              </p>
              <p className="mt-2.5 text-[13px]" style={{ color: C.muted }}>
                Two banks, Fidelity and GCB, returned redirects our reader
                could not follow. We say so rather than counting them either
                way.
              </p>
            </div>
          </div>
        </div>

        {/* And the arithmetic, which is the reason the rate matters. */}
        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Why the rate decides everything
        </h2>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          Prime residential property in Accra is reported to yield around 8% to
          11% a year gross — before vacancy, maintenance, management, insurance
          and the 8% tax on residential rental income.
        </p>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          Set that against the one published rate. A GH₵800,000 mortgage at 18%
          costs about GH₵144,000 in first-year interest. A GH₵1m property
          yielding 9% brings in about GH₵90,000 of rent.
        </p>
        <div
          className="mt-4 rounded-2xl p-5"
          style={{ background: "#FFF8EC", border: `1px solid ${C.gold}` }}
        >
          <p className="text-[14.5px] font-bold">
            The rent does not cover the interest, before any costs at all
          </p>
          <p
            className="mt-2 text-[14px] leading-relaxed"
            style={{ color: C.muted }}
          >
            That gap has to be made up from somewhere — from the buyer&rsquo;s
            own income, or from the property appreciating faster than the
            shortfall accumulates. Which is a bet on price growth rather than an
            income investment, and worth recognising as one before signing for
            twenty years.
          </p>
          <p
            className="mt-2.5 text-[14px] leading-relaxed"
            style={{ color: C.muted }}
          >
            The yield figures above are from published market research rather
            than our own data, and we have not verified them. Everything else on
            this page comes from the lenders themselves.
          </p>
        </div>

        {/* Terms, as prose per bank. A table would be empty cells. */}
        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What each bank does publish
        </h2>
        <p className="mt-2 text-[13.5px]" style={{ color: C.muted }}>
          Loan-to-value, tenor, currencies, eligibility — each bank states a
          different subset, which is why this is a list rather than a table.
        </p>
        <div className="mt-4 space-y-2">
          {TERMS_ORDER.map((slug) => (
            <Link
              key={slug}
              href={`/lenders/${slug}`}
              className="block rounded-2xl p-4 transition-shadow hover:shadow-md"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <span className="text-[13.5px] font-semibold" style={{ color: C.deep }}>
                {slug
                  .split("-")
                  .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                  .join(" ")}{" "}
                &rarr;
              </span>
            </Link>
          ))}
        </div>
        <p className="mt-3 text-[13px] leading-relaxed" style={{ color: C.muted }}>
          Each lender page carries what they publish, with the date we read it.
          Terms about who may borrow from abroad are on the{" "}
          <Link
            href="/investing-from-abroad"
            className="font-semibold underline underline-offset-4"
            style={{ color: C.deep }}
          >
            diaspora page
          </Link>
          .
        </p>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Five things to ask before you borrow
        </h2>
        <ol className="mt-4 space-y-3">
          {ASK.map((q, i) => (
            <li key={i} className="flex gap-3">
              <span
                className="mt-0.5 shrink-0 text-[13px] font-bold tabular-nums"
                style={{ color: C.gold }}
              >
                {i + 1}
              </span>
              <span className="text-[14.5px] leading-relaxed">{q}</span>
            </li>
          ))}
        </ol>

        <ShareThis
          path="/mortgages"
          audience="somebody buying a home in Ghana"
          message="One Ghanaian bank of twenty-one publishes a mortgage rate. The market leader is not it."
        />

        <DataProvenance
          title="Ghanaian mortgage rates and published terms"
          source="the banks' own websites"
          covering="21 of 23 licensed banks, plus the Bank of Ghana Mortgage Finance register"
          checked="September 2026"
          method="Each bank's site navigation followed from its home page rather than addresses guessed. Rates recorded only where the lender publishes a number; terms recorded as published. Two banks were unreachable and are counted as neither."
          pageUrl="https://cedafin.com/mortgages"
        />

        <p className="mt-6 text-[12.5px] leading-relaxed" style={{ color: C.muted }}>
          {BRAND.legalStatus} We are not a credit broker and do not arrange
          finance. If you lend and we have your terms wrong, or you publish a
          rate we have missed, tell us and we will correct it the same day.
        </p>
      </div>

      <Footer />
    </main>
  );
}
