"use client";

/**
 * app/funding/match/page.tsx — eight questions, then what a business could ask for.
 *
 * BUILT COMPLETE, FILLED IN LATER. Every question a lender would ask is here,
 * and every field it maps to exists in the schema. Today most of those fields
 * are empty for all 23 banks, because Bank of Ghana's APR report publishes
 * averages rather than terms, and a check of 24 bank websites found none
 * publishing SME lending criteria. So the flow runs, filters on what exists,
 * and says exactly which answers could not be matched and why.
 *
 * THAT GAP IS THE PRODUCT ARGUMENT, NOT A DEFECT TO HIDE. A business seeing
 * "we couldn't check whether you qualify, because no Ghanaian bank publishes
 * its criteria" learns something true and useful. It is also the reason a
 * lender should send us their terms — the page shows them precisely what their
 * silence looks like to a borrower.
 *
 * WHAT IS AND IS NOT A RECOMMENDATION
 *
 *   FILTERING on amount, term and category applies facts the business stated
 *   to figures the regulator published. No licence needed.
 *
 *   MATCHING a business to a lender for a fee is credit broking, and telling
 *   them which facility suits them is advice. Both are built and both stay
 *   behind platform_settings.lead_routing_enabled and COMPLIANCE_PHASE.
 *
 * NOTHING IS STORED. Trading history, revenue band, what the money is for —
 * that is commercially sensitive and, with a named contact attached, personal
 * data under Ghana's Data Protection Act 2012. It lives in browser state and
 * goes nowhere. The enquiry table exists for when routing is licensed; until
 * then the form does not submit.
 */

import Link from "next/link";
import { useMemo, useState } from "react";

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

const GHS = new Intl.NumberFormat("en-GH", {
  style: "currency",
  currency: "GHS",
  maximumFractionDigits: 0,
});

interface Loan {
  id: string;
  slug: string;
  name: string;
  provider: string;
  providerSlug: string;
  category: string;
  tenorYears: number;
  lendingRatePct: number | null;
  aprPct: number | null;
  feeGapPct: number | null;
}

type Answers = {
  who?: string;
  registered?: string;
  trading?: string;
  sector?: string;
  amountGhs?: number;
  termYears?: number;
  purpose?: string;
  security?: string;
  revenue?: string;
};

/**
 * Bank of Ghana's own sectoral categories, so anything gathered here is
 * comparable with their published credit shares. Their March 2026 figures:
 * services 36.7%, commerce and finance 23.0%, manufacturing 11.0%, and
 * agriculture 4.5% — the last against a sector employing a large share of the
 * country. That gap is worth showing a farmer who lands on this page.
 */
/**
 * Grouped, because thirteen flat options gave no hint that seven of them are a
 * single category to Bank of Ghana. A founder should see their own words —
 * "e-commerce", not "services" — while also seeing which regulatory bucket
 * their business sits in, since that is how a bank's credit committee will
 * think about the application too.
 *
 * The heading is the group; the options underneath are what someone selects.
 */
const SECTORS: readonly (readonly [string, string, string?])[] = [
  ["agriculture", "Agriculture, forestry or fishing"],
  ["commerce", "Trading, retail or wholesale"],
  ["manufacturing", "Manufacturing or processing"],
  ["construction", "Construction or property"],
  ["transport", "Transport or logistics"],
  ["technology", "Technology or software", "Services"],
  ["ecommerce", "E-commerce or online retail", "Services"],
  ["fintech", "Fintech or payments", "Services"],
  ["creative", "Creative, media or professional services", "Services"],
  ["hospitality", "Hospitality, food or tourism", "Services"],
  ["health_edu", "Health or education", "Services"],
  ["services", "Other services", "Services"],
  ["other", "Something else"],
] as const;

/**
 * Ghanaian businesses do not describe themselves as "services", but Bank of
 * Ghana's credit statistics only count that way. So the list shows what a
 * founder would recognise and maps underneath to the regulator's taxonomy —
 * which keeps the sector share figure honest.
 *
 * A software company, an online shop and a payments startup are all "services"
 * to BoG. Presenting them as separate sectors with no credit share attached
 * would lose the one genuinely useful thing this question produces: telling
 * someone what proportion of national bank lending reaches businesses like
 * theirs. Better to show them their own words and be accurate underneath.
 *
 * Hospitality and health/education are also within BoG's services aggregate.
 * If the regulator ever breaks these out, the mapping is the only thing that
 * changes.
 */
const SECTOR_TO_BOG: Record<string, string> = {
  technology: "services",
  ecommerce: "services",
  fintech: "services",
  creative: "services",
  hospitality: "services",
  health_edu: "services",
  services: "services",
  agriculture: "agriculture",
  commerce: "commerce",
  manufacturing: "manufacturing",
  construction: "construction",
  transport: "transport",
};

/** How BoG names the aggregate a sector falls into, for the share sentence. */
const BOG_SECTOR_LABEL: Record<string, string> = {
  services: "services",
  commerce: "commerce and finance",
  manufacturing: "manufacturing",
  agriculture: "agriculture, forestry and fishing",
};

const SECTOR_CREDIT_SHARE: Record<string, number> = {
  services: 36.7,
  commerce: 23.0,
  manufacturing: 11.0,
  agriculture: 4.5,
};

const CATEGORY_OF_WHO: Record<string, string> = {
  business: "sme_credit",
  large: "corporate_credit",
  personal: "personal_credit",
};

const QUESTIONS = [
  {
    key: "who",
    q: "Who is borrowing?",
    why: "Banks price small business, corporate and personal credit differently.",
    options: [
      ["business", "A small or medium business"],
      ["large", "A large company"],
      ["personal", "Me, personally"],
    ],
  },
  {
    key: "registered",
    q: "Is the business registered?",
    why: "Every lender asks. None publish what they'll accept.",
    options: [
      ["yes", "Yes, formally registered"],
      ["sole", "Sole proprietor"],
      ["no", "Not yet registered"],
      ["na", "Not applicable"],
    ],
  },
  {
    key: "trading",
    q: "How long have you been trading?",
    why: "The most common reason an application is refused.",
    options: [
      ["under1", "Less than a year"],
      ["1to2", "1 to 2 years"],
      ["3to5", "3 to 5 years"],
      ["over5", "More than 5 years"],
    ],
  },
  {
    key: "sector",
    q: "What does the business do?",
    why: "Bank of Ghana publishes how credit is split across sectors.",
    options: SECTORS,
  },
  {
    key: "amount",
    q: "How much do you need?",
    why: "Shown as a cost in cedis against each lender's rate.",
    options: [
      ["10000", "Under GH₵20,000"],
      ["50000", "GH₵20,000 to 100,000"],
      ["250000", "GH₵100,000 to 500,000"],
      ["1000000", "GH₵500,000 to 2 million"],
      ["5000000", "More than GH₵2 million"],
    ],
  },
  {
    key: "term",
    q: "Over how long would you repay?",
    why: "Filters to the rates banks report for that term.",
    options: [
      ["1", "About a year"],
      ["3", "About three years"],
      ["5", "About five years"],
    ],
  },
  {
    key: "purpose",
    q: "What is the money for?",
    why: "No Ghanaian bank publishes rates by purpose — recorded, not filtered.",
    options: [
      ["working_capital", "Day-to-day working capital"],
      ["equipment", "Equipment or machinery"],
      ["vehicle", "Vehicles"],
      ["stock", "Stock or inventory"],
      ["trade", "Importing or exporting"],
      ["premises", "Premises or construction"],
      ["expansion", "Expanding or opening up"],
      ["refinance", "Replacing existing debt"],
    ],
  },
  {
    key: "security",
    q: "Do you have security to offer?",
    why: "Decides the rate you're offered. No bank publishes its requirement.",
    options: [
      ["property", "Property or land"],
      ["equipment", "Equipment or vehicles"],
      ["receivables", "Invoices or receivables"],
      ["cash", "Cash or investments"],
      ["none", "Nothing to pledge"],
    ],
  },
  {
    key: "revenue",
    q: "Roughly what does the business turn over each month?",
    why: "For affordability guidance, which is switched off.",
    options: [
      ["under10k", "Under GH₵10,000"],
      ["10to50k", "GH₵10,000 to 50,000"],
      ["50to250k", "GH₵50,000 to 250,000"],
      ["over250k", "More than GH₵250,000"],
      ["prefer", "Rather not say"],
    ],
  },
] as const;

const AMOUNT_PRESETS = [10000, 50000, 250000, 1000000];

export default function FundingMatchPage() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [loans, setLoans] = useState<Loan[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Live controls on the results page, for the two things the filter acts on.
  const [tryAmount, setTryAmount] = useState<number | null>(null);
  const [tryTerm, setTryTerm] = useState<number | null>(null);

  const done = step >= QUESTIONS.length;

  async function loadLoans() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/lending");
      if (!res.ok) throw new Error(`request failed (${res.status})`);
      setLoans(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "could not load lenders");
    } finally {
      setLoading(false);
    }
  }

  function answer(key: string, value: string) {
    setAnswers((a) => ({
      ...a,
      ...(key === "amount"
        ? { amountGhs: Number(value) }
        : key === "term"
          ? { termYears: Number(value) }
          : { [key]: value }),
    }));
    advance();
  }

  function advance() {
    setStep((s) => {
      const next = s + 1;
      if (next >= QUESTIONS.length && !loans) void loadLoans();
      return next;
    });
  }

  const outcome = useMemo(() => {
    if (!loans) return null;
    const amount = tryAmount ?? answers.amountGhs;
    const term = tryTerm ?? answers.termYears;
    const category = answers.who ? CATEGORY_OF_WHO[answers.who] : undefined;

    const matches = loans.filter((l) => {
      if (category && l.category !== category) return false;
      if (term && l.tenorYears !== term) return false;
      return true;
    });
    matches.sort((a, b) => (a.aprPct ?? 999) - (b.aprPct ?? 999));

    // Everything we asked that nothing published can be matched against.
    // Named individually, because "some criteria unavailable" tells a business
    // nothing, and naming them is what makes the ask to lenders concrete.
    const unmatched: string[] = [];
    if (answers.registered) unmatched.push("whether your business is registered");
    if (answers.trading) unmatched.push("how long you've been trading");
    if (answers.sector) unmatched.push("your sector");
    if (answers.purpose) unmatched.push("what the money is for");
    if (answers.security) unmatched.push("what security you can offer");
    if (answers.revenue && answers.revenue !== "prefer")
      unmatched.push("your turnover");

    const warnings: string[] = [];
    if (answers.trading === "under1") {
      warnings.push(
        "Most Ghanaian banks want to see two or more years of trading before lending to a business. Under a year, expect to be asked for personal security or turned down — and none of them publish the threshold, so you'll have to ask.",
      );
    }
    if (answers.security === "none") {
      warnings.push(
        "Unsecured business lending is scarce in Ghana. Bank of Ghana's capital rules make small unsecured loans expensive for banks to hold, so most will ask for something pledged.",
      );
    }
    if (answers.registered === "no") {
      warnings.push(
        "Banks lend to registered businesses. Without registration you'd be borrowing personally, which is a different product and usually dearer.",
      );
    }

    const bogSector = answers.sector
      ? (SECTOR_TO_BOG[answers.sector] ?? answers.sector)
      : undefined;
    const share = bogSector ? SECTOR_CREDIT_SHARE[bogSector] : undefined;
    const shareLabel = bogSector ? BOG_SECTOR_LABEL[bogSector] : undefined;
    /** True when the person's own words differ from the regulator's bucket. */
    const shareIsAggregate = Boolean(
      bogSector && answers.sector && bogSector !== answers.sector,
    );

    return {
      matches,
      unmatched,
      warnings,
      share,
      shareLabel,
      shareIsAggregate,
      amount,
      term,
    };
  }, [loans, answers, tryAmount, tryTerm]);

  const q = QUESTIONS[step];

  return (
    <main className="min-h-screen" style={{ background: C.bg, color: C.ink }}>
      <div
        className="w-full px-5 py-2 text-center text-[11px] font-medium tracking-wide text-white"
        style={{ background: "linear-gradient(90deg, #7A3E12, #E8A33D)" }}
      >
        Your answers stay in this browser · nothing is saved or sent to any
        lender
      </div>

      <header className="mx-auto max-w-2xl px-5 pt-6">
        <Link href="/" className="text-[19px] font-bold" style={{ color: C.deep }}>
          Cedafin
        </Link>
      </header>

      <div className="mx-auto max-w-2xl px-5 py-8">
        {!done && q && (
          <>
            <div className="flex items-center gap-2">
              {QUESTIONS.map((_, i) => (
                <span
                  key={i}
                  className="h-1 flex-1 rounded-full"
                  style={{ background: i <= step ? C.gold : C.rule }}
                />
              ))}
            </div>
            <p
              className="mt-4 text-[11px] uppercase tracking-wider"
              style={{ color: C.muted }}
            >
              Question {step + 1} of {QUESTIONS.length}
            </p>

            <h1 className="mt-2 text-[1.7rem] font-bold leading-tight sm:text-[2.1rem]">
              {q.q}
            </h1>
            <p className="mt-2 text-[12.5px]" style={{ color: C.muted }}>
              {q.why}
            </p>

            <div className="mt-6 space-y-2.5">
              {q.options.map((opt, oi) => {
                const [value, label] = opt as readonly [string, string, string?];
                const group = (opt as readonly [string, string, string?])[2];
                const prevGroup =
                  oi > 0
                    ? (q.options[oi - 1] as readonly [string, string, string?])[2]
                    : undefined;
                const heading = group && group !== prevGroup ? group : null;
                const stored = (answers as Record<string, unknown>)[
                  q.key === "amount"
                    ? "amountGhs"
                    : q.key === "term"
                      ? "termYears"
                      : q.key
                ];
                const chosen =
                  stored ===
                  (q.key === "amount" || q.key === "term" ? Number(value) : value);
                return (
                  <div key={value}>
                    {heading && (
                      <p
                        className="mb-2 mt-5 text-[11px] font-bold uppercase tracking-[0.14em]"
                        style={{ color: C.muted }}
                      >
                        {heading}
                        <span className="ml-2 font-medium normal-case tracking-normal opacity-80">
                          — counted together by Bank of Ghana
                        </span>
                      </p>
                    )}
                    <button
                      onClick={() => answer(q.key, value)}
                      className="w-full rounded-2xl px-5 py-4 text-left text-[14.5px] font-medium"
                      style={{
                        background: chosen ? `${C.gold}1A` : C.card,
                        border: `1px solid ${chosen ? C.gold : C.rule}`,
                        color: C.ink,
                        marginLeft: group ? 12 : 0,
                        width: group ? "calc(100% - 12px)" : "100%",
                      }}
                    >
                      {label}
                    </button>
                  </div>
                );
              })}
            </div>

            <div className="mt-6 flex items-center justify-between">
              <button
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={step === 0}
                className="text-[13px] disabled:opacity-40"
                style={{ color: C.muted }}
              >
                ← Back
              </button>
              <button
                onClick={advance}
                className="rounded-full px-5 py-2.5 text-[13.5px] font-bold text-white"
                style={{ background: "#7A3E12" }}
              >
                Skip →
              </button>
            </div>
          </>
        )}

        {done && (
          <>
            <h1 className="text-[1.9rem] font-bold leading-tight sm:text-[2.4rem]">
              What this would cost you
            </h1>

            {loading && (
              <p className="mt-6 text-[14px]" style={{ color: C.muted }}>
                Checking the lenders…
              </p>
            )}
            {error && (
              <p className="mt-6 text-[14px]" style={{ color: C.clay }}>
                {error}
              </p>
            )}

            {outcome && (
              <>
                {outcome.warnings.map((w) => (
                  <p
                    key={w}
                    className="mt-5 rounded-2xl px-5 py-4 text-[13.5px] leading-relaxed"
                    style={{ background: `${C.gold}1A` }}
                  >
                    <strong>Worth knowing.</strong> {w}
                  </p>
                ))}

                {/* The sector line, where BoG publishes a share for it. A
                    farmer seeing 4.5% learns something no bank will tell them. */}
                {outcome.share !== undefined && (
                  <p
                    className="mt-5 rounded-2xl px-5 py-4 text-[13.5px] leading-relaxed"
                    style={{ background: C.card, border: `1px solid ${C.rule}` }}
                  >
                    Bank of Ghana reports that{" "}
                    <strong>{outcome.share}%</strong> of all bank credit in
                    Ghana goes to {outcome.shareLabel ?? "your sector"}
                    {outcome.shareIsAggregate && (
                      <>
                        {" "}
                        — the category the regulator counts your business under
                      </>
                    )}
                    {outcome.share < 10 && (
                      <>
                        {" "}
                        — one of the smallest shares in the economy. Expect
                        fewer lenders willing to look at it, and understand
                        that has more to do with the sector than with your
                        business
                      </>
                    )}
                    .
                  </p>
                )}

                {/* Live controls, for the two things the filter acts on. */}
                <section
                  className="mt-6 rounded-2xl p-5"
                  style={{ background: C.card, border: `1px solid ${C.rule}` }}
                >
                  <p
                    className="text-[12px] font-semibold uppercase tracking-wider"
                    style={{ color: C.muted }}
                  >
                    Change the amount or the term
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {AMOUNT_PRESETS.map((v) => {
                      const on = (tryAmount ?? answers.amountGhs) === v;
                      return (
                        <button
                          key={v}
                          onClick={() => setTryAmount(v)}
                          className="rounded-full px-4 py-2 text-[13px] font-semibold"
                          style={{
                            background: on ? "#7A3E12" : C.bg,
                            color: on ? "#fff" : C.ink,
                            border: `1px solid ${on ? "#7A3E12" : C.rule}`,
                          }}
                        >
                          {GHS.format(v)}
                        </button>
                      );
                    })}
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {[1, 3, 5].map((y) => {
                      const on = (tryTerm ?? answers.termYears) === y;
                      return (
                        <button
                          key={y}
                          onClick={() => setTryTerm(y)}
                          className="rounded-full px-4 py-2 text-[13px] font-semibold"
                          style={{
                            background: on ? `${C.gold}26` : C.bg,
                            color: on ? "#7A3E12" : C.muted,
                            border: `1px solid ${on ? C.gold : C.rule}`,
                          }}
                        >
                          {y} year{y > 1 ? "s" : ""}
                        </button>
                      );
                    })}
                  </div>
                </section>

                <p className="mt-5 text-[14px]" style={{ color: C.muted }}>
                  {outcome.matches.length} lenders report a rate for this.
                  Cheapest first.
                </p>

                <ol className="mt-5 space-y-3">
                  {outcome.matches.map((l, i) => {
                    const amt = outcome.amount;
                    const yearly =
                      amt && l.aprPct !== null ? (amt * l.aprPct) / 100 : null;
                    return (
                      <li
                        key={l.id}
                        className="rounded-2xl p-5"
                        style={{
                          background: C.card,
                          border: `1px solid ${i === 0 ? C.gold : C.rule}`,
                        }}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <h2 className="text-[15.5px] font-bold">
                            {l.provider}
                          </h2>
                          <div className="text-right">
                            <p className="text-[1.4rem] font-bold tabular-nums leading-none">
                              {l.aprPct !== null
                                ? `${l.aprPct.toFixed(2)}%`
                                : "—"}
                            </p>
                            <p
                              className="text-[10.5px]"
                              style={{ color: C.muted }}
                            >
                              all-in cost a year
                            </p>
                          </div>
                        </div>

                        {yearly !== null && (
                          <div
                            className="mt-4 rounded-xl px-4 py-3 text-[12.5px]"
                            style={{ background: C.bg }}
                          >
                            Borrowing <strong>{GHS.format(amt!)}</strong> would
                            cost about{" "}
                            <strong style={{ color: C.clay }}>
                              {GHS.format(yearly)}
                            </strong>{" "}
                            a year in interest and charges
                            {outcome.term && outcome.term > 1 && (
                              <>
                                {" "}
                                — roughly{" "}
                                {GHS.format(yearly * outcome.term)} over{" "}
                                {outcome.term} years
                              </>
                            )}
                            .
                            {l.lendingRatePct !== null &&
                              l.feeGapPct !== null &&
                              l.feeGapPct > 0.05 && (
                                <>
                                  {" "}
                                  Their advertised rate is{" "}
                                  {l.lendingRatePct.toFixed(2)}% — fees add{" "}
                                  {l.feeGapPct.toFixed(2)} points.
                                </>
                              )}
                          </div>
                        )}

                        <p className="mt-3 text-[12px]" style={{ color: C.muted }}>
                          <Link
                            href={`/lenders/${l.providerSlug}`}
                            className="underline underline-offset-2"
                            style={{ color: C.deep }}
                          >
                            What we know about this lender
                          </Link>
                        </p>
                      </li>
                    );
                  })}
                </ol>

                {outcome.matches.length === 0 && (
                  <p
                    className="mt-5 rounded-2xl px-5 py-5 text-[13.5px] leading-relaxed"
                    style={{ background: C.card, border: `1px solid ${C.rule}` }}
                  >
                    No bank reports a rate for that combination. Bank of Ghana
                    publishes one, three and five-year figures only, and not
                    every bank reports every term.
                  </p>
                )}

                <p
                  className="mt-6 rounded-2xl px-5 py-4 text-[12.5px] leading-relaxed"
                  style={{ background: `${C.gold}1A` }}
                >
                  <strong>These are indicative rates, not offers.</strong> Bank
                  of Ghana publishes an average of what each bank charged, so
                  borrowers can compare. What you are actually offered depends
                  on the bank&rsquo;s assessment of your business. Treat this as
                  where to start asking.
                </p>

                {/* What we asked and could not use. */}
                {outcome.unmatched.length > 0 && (
                  <section
                    className="mt-8 rounded-3xl p-6"
                    style={{ background: C.card, border: `1px dashed ${C.rule}` }}
                  >
                    <h2 className="text-[16px] font-bold">
                      What we couldn&rsquo;t check
                    </h2>
                    <p
                      className="mt-3 text-[13.5px] leading-relaxed"
                      style={{ color: C.muted }}
                    >
                      We asked about {outcome.unmatched.join(", ")} — and
                      couldn&rsquo;t use any of it. Not one Ghanaian bank
                      publishes its lending criteria: not a minimum, not a
                      trading-history threshold, not what security it wants. We
                      checked all 24 bank websites.
                    </p>
                    <p
                      className="mt-3 text-[13.5px] leading-relaxed"
                      style={{ color: C.muted }}
                    >
                      So the list above is ordered on cost, which is the one
                      thing the regulator makes public. When lenders send us
                      their terms, these answers will narrow it properly.
                    </p>
                  </section>
                )}

                {/* Routing and suitability: built, visibly withheld. */}
                <section
                  className="mt-4 rounded-3xl p-6"
                  style={{ background: C.card, border: `1px dashed ${C.rule}` }}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider"
                      style={{ background: `${C.clay}12`, color: C.clay }}
                    >
                      Switched off
                    </span>
                    <h2 className="text-[16px] font-bold">
                      Send this to the lenders
                    </h2>
                  </div>
                  <p
                    className="mt-3 text-[13.5px] leading-relaxed"
                    style={{ color: C.muted }}
                  >
                    We could pass your details to the lenders most likely to say
                    yes, and tell you which facility suits you. Being paid to
                    introduce a borrower to a lender is credit broking, and
                    it&rsquo;s licensed — regardless of which side pays. We
                    don&rsquo;t hold that licence yet, so it stays off.
                  </p>
                  <p className="mt-3 text-[12.5px]" style={{ color: C.muted }}>
                    Until then, the lender pages above carry the contact details
                    Bank of Ghana holds for each bank. You approach them
                    directly, and nobody pays us for it.
                  </p>
                </section>

                <div className="mt-8 flex flex-wrap gap-3">
                  <button
                    onClick={() => {
                      setAnswers({});
                      setStep(0);
                      setTryAmount(null);
                      setTryTerm(null);
                    }}
                    className="rounded-full px-5 py-2.5 text-[13.5px] font-bold text-white"
                    style={{ background: "#7A3E12" }}
                  >
                    Start again
                  </button>
                  <Link
                    href="/funding"
                    className="rounded-full px-5 py-2.5 text-[13.5px] font-semibold"
                    style={{
                      background: C.card,
                      border: `1px solid ${C.rule}`,
                      color: C.ink,
                    }}
                  >
                    See every lender instead
                  </Link>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </main>
  );
}
