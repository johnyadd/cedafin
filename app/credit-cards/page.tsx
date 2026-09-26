import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import DataProvenance from "@/components/DataProvenance";
import Footer from "@/components/Footer";
import ShareThis from "@/components/ShareThis";
import { getProviderCharges, type ProviderCharge } from "@/lib/data/funds";

/**
 * app/credit-cards/page.tsx - what a Ghanaian credit card costs, from the
 * banks' own tariff guides.
 *
 * WHAT IS READ FROM THE DATABASE
 * Everything priced: provider_charges rows with category = credit_card,
 * loaded by load_provider_charges.py from each bank's tariff guide. A card
 * appears here the day its guide is loaded; nothing on this page names a bank.
 *
 * WHY THE WORDING AND NOT A NUMBER
 * Banks quote cards differently: Absa and Zenith give an annual rate, Republic
 * a monthly one; Zenith charges cash and purchases differently. Each cell shows
 * the bank's own words. Where a rate is monthly, the annual equivalent is shown
 * underneath as labelled working, never in place of the published figure.
 *
 * WHY "NOT PUBLISHED" AND NOT A BLANK
 * A blank reads as missing data. "Not published" is the finding: the bank's
 * guide prices the card but does not state what it costs to borrow on it.
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
  bg: "#F2F6F9",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
};

export const metadata = {
  title: "Ghanaian credit card rates and fees, from the banks' own tariff guides",
  description:
    "Interest rates, annual fees, late payment and foreign transaction charges on Ghanaian credit cards, exactly as each bank prints them in its tariff guide, dated and sourced.",
  keywords: ["credit card Ghana", "credit card interest rate Ghana", "Ghana bank charges", "tariff guide Ghana"],
};

export const revalidate = 3600;

/** The rows of every card, and which charge keys feed each row. */
const ROWS: { label: string; keys: string[] }[] = [
  { label: "Interest rate", keys: ["interest", "interest_purchases", "interest_cash"] },
  { label: "Annual fee", keys: ["annual_fee"] },
  { label: "Monthly fee", keys: ["monthly_maintenance", "maintenance"] },
  { label: "Issuance fee", keys: ["issuance"] },
  { label: "Late payment", keys: ["late_payment"] },
  { label: "Cash withdrawal", keys: ["cash_advance", "cash_withdrawal_local"] },
  { label: "Over the limit", keys: ["over_limit"] },
  { label: "Foreign transactions", keys: ["foreign_transactions", "cross_border", "scheme_markup"] },
];
const INTEREST_KEYS = ROWS[0].keys;

const WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"];

/**
 * A guide dated only by month ("September 2026") is stored as the 1st of that
 * month. Showing "1 September 2026" would claim a day the guide never states,
 * so a 1st is shown as month and year only.
 */
function fmtDate(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(`${iso}T00:00:00Z`);
  return d.toLocaleDateString("en-GB", {
    ...(iso.endsWith("-01") ? {} : { day: "numeric" as const }),
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** Annual equivalents of a monthly rate: labelled working, never the headline figure. */
function monthlyWorking(c: ProviderCharge): string | null {
  if (c.ratePeriod !== "month" || c.rate === null || !INTEREST_KEYS.includes(c.chargeKey)) return null;
  const simple = c.rate * 12 * 100;
  const compounded = (Math.pow(1 + c.rate, 12) - 1) * 100;
  return `${(c.rate * 100).toFixed(2)}% a month is ${simple.toFixed(1)}% a year simple, about ${compounded.toFixed(1)}% compounded monthly.`;
}

export default async function CreditCardsPage() {
  const charges = await getProviderCharges("credit_card");

  // One card per provider + product label, in provider order.
  const cards = new Map<string, ProviderCharge[]>();
  for (const c of [...charges].sort((a, b) =>
    (a.providerName + a.productLabel).localeCompare(b.providerName + b.productLabel),
  )) {
    const k = `${c.providerSlug}|${c.productLabel}`;
    if (!cards.has(k)) cards.set(k, []);
    cards.get(k)!.push(c);
  }

  const withRate = new Set(
    charges.filter((c) => INTEREST_KEYS.includes(c.chargeKey) && c.rate !== null).map((c) => c.providerSlug),
  );
  const allBanks = new Set(charges.map((c) => c.providerSlug));
  const n = withRate.size;
  const headline = `${WORDS[n] ?? String(n)} Ghanaian bank${n === 1 ? "" : "s"} publish${n === 1 ? "es" : ""} a credit card interest rate`;

  // Group cards under their bank, keeping the source line once per document.
  const banks = new Map<string, { name: string; cards: [string, ProviderCharge[]][] }>();
  for (const [k, rows] of cards) {
    const slug = rows[0].providerSlug;
    if (!banks.has(slug)) banks.set(slug, { name: rows[0].providerName, cards: [] });
    banks.get(slug)!.cards.push([k, rows]);
  }

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div className="mx-auto max-w-3xl px-5 py-12 sm:py-16">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: C.deep }}>
          Borrowing on a card in Ghana
        </p>
        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.1] sm:text-[2.4rem]"
          style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.02em" }}
        >
          {headline}
        </h1>
        <p className="mt-5 text-[16.5px] leading-relaxed" style={{ color: C.muted }}>
          In September 2026 we read the tariff guide of every Ghanaian bank we could reach. These are the
          credit cards they price, in each bank&rsquo;s own words, with the date of the guide it comes from.
          {allBanks.size > n
            ? " Where a bank prices the card but states no interest rate, the table says so."
            : ""}
        </p>

        {banks.size === 0 ? (
          <p className="mt-8 text-[15px]" style={{ color: C.muted }}>
            None currently held.
          </p>
        ) : (
          <div className="mt-8 space-y-5">
            {[...banks.entries()].map(([slug, bank]) => {
              const docs = new Map<string, ProviderCharge>();
              for (const [, rows] of bank.cards) for (const r of rows) if (r.sourceTitle) docs.set(r.sourceTitle, r);
              return (
                <section
                  key={slug}
                  className="overflow-hidden rounded-2xl"
                  style={{ background: C.card, border: `1px solid ${C.rule}` }}
                >
                  <div className="px-5 py-3 text-white" style={{ background: C.deep }}>
                    <p className="text-[15px] font-bold">{bank.name}</p>
                    {[...docs.values()].map((d) => (
                      <p key={d.sourceTitle} className="text-[11.5px] opacity-90">
                        {d.sourceUrl ? (
                          <a href={d.sourceUrl} className="underline underline-offset-2" rel="noopener noreferrer" target="_blank">
                            {d.sourceTitle}
                          </a>
                        ) : (
                          d.sourceTitle
                        )}
                        {fmtDate(d.documentDate) ? ` \u00b7 dated ${fmtDate(d.documentDate)}` : ""}
                      </p>
                    ))}
                  </div>

                  {bank.cards.map(([k, rows]) => (
                    <div key={k} className="border-t p-5" style={{ borderColor: C.rule }}>
                      <p className="text-[15px] font-semibold">{rows[0].productLabel || "Credit card"}</p>
                      <dl className="mt-3 divide-y text-[13.5px]" style={{ borderColor: C.rule }}>
                        {ROWS.map((row) => {
                          const hits = rows.filter((r) => row.keys.includes(r.chargeKey));
                          const isInterest = row.keys === INTEREST_KEYS;
                          if (hits.length === 0 && !isInterest) return null;
                          return (
                            <div key={row.label} className="grid grid-cols-[9rem_1fr] gap-3 py-2">
                              <dt style={{ color: C.muted }}>{row.label}</dt>
                              <dd>
                                {hits.length === 0 ? (
                                  <span className="font-semibold" style={{ color: C.deep }}>
                                    Not published
                                  </span>
                                ) : (
                                  hits.map((h) => (
                                    <div key={h.chargeKey}>
                                      <span className="font-semibold">{h.wording}</span>
                                      {monthlyWorking(h) && (
                                        <p className="mt-0.5 text-[12px]" style={{ color: C.muted }}>
                                          Working: {monthlyWorking(h)}
                                        </p>
                                      )}
                                    </div>
                                  ))
                                )}
                              </dd>
                            </div>
                          );
                        })}
                      </dl>
                    </div>
                  ))}

                  {slug === "absa-bank-ghana" && (
                    <p className="border-t px-5 py-3 text-[12.5px] leading-relaxed" style={{ borderColor: C.rule, color: C.muted }}>
                      Absa&rsquo;s retail and Premier tariff guides, both dated September 2026, give the Platinum card
                      different interest rates. Neither guide explains the difference.
                    </p>
                  )}
                </section>
              );
            })}
          </div>
        )}

        <h2 className="mt-12 text-[1.4rem] font-bold" style={{ fontFamily: "var(--font-display)" }}>
          Reading these rates
        </h2>
        <p className="mt-3 text-[15px] leading-relaxed">
          An annual rate and a monthly rate are not the same thing. A card charging a rate each month costs
          more over a year than the monthly figure times twelve, because interest is charged on interest.
          Where a bank publishes a monthly rate, the annual equivalent is worked out beneath it and marked as
          working.
        </p>
        <p className="mt-3 text-[15px] leading-relaxed">
          None of these figures includes the charges a card collects in use: fees for cash withdrawals, for
          paying abroad or for going over the limit. They are listed separately for each card because they
          can cost more than the interest.
        </p>

        <ShareThis
          path="/credit-cards"
          audience="somebody choosing a credit card in Ghana"
          message="What Ghanaian credit cards cost, from the banks' own tariff guides."
        />

        <DataProvenance
          title="Ghanaian credit card rates and fees"
          source="the banks' own tariff guides"
          covering="the tariff guides of the Ghanaian banks we could reach, read September 2026"
          checked="September 2026"
          method="Each charge is copied from the bank's tariff guide in its own words, with the guide's title and date. A monthly rate is shown as published, with its annual equivalent as labelled working. A card priced without an interest rate is marked 'Not published'."
          pageUrl="https://cedafin.com/credit-cards"
        />
      </div>
      <Footer />
    </main>
  );
}
