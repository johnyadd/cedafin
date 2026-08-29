/**
 * app/funding/page.tsx — what borrowing costs a Ghanaian business.
 *
 * WHY /funding AND NOT /borrow
 * "Borrow" is right in the database — it is the opposite of "invest" and names
 * the direction money moves. But a founder does not think "I need to borrow",
 * they think "I need funding", and funding covers equity and grants too. The
 * URL is the expensive thing to change later, so it takes the broader word;
 * the heading stays specific to what is actually here.
 *
 * THE FINDING THIS PAGE EXISTS FOR
 * A Ghanaian SME can pay 11.03% or 33.58% for the same one-year facility, in
 * the same month, from two licensed banks. Three times the cost. Bank of Ghana
 * publishes this monthly and it reaches almost nobody.
 *
 * TWO THINGS THE PAGE MUST NOT DO
 *
 *   TREAT A RATE AS A QUOTE. BoG says plainly that a typical customer may be
 *   offered something different after assessment. Every figure here is
 *   indicative and the page says so beside the numbers, not in a footer. A
 *   business that reads 11.03% as an offer and budgets on it has been misled
 *   by us, not by the bank.
 *
 *   HIDE THE FEES. The advertised lending rate and the APR are both shown
 *   because the gap between them is the point: Agricultural Development Bank
 *   lends at 19.59% and costs 28.13%, while Access Bank's gap is 0.03. Rank on
 *   the headline rate and those two look comparable. They are not.
 */

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";
import { notFound } from "next/navigation";

import { BRAND } from "@/lib/brand";
import { creditLabel, getLending, type LendingRow } from "@/lib/data/funds";

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
  ink: "#0C1F1C",
  deep: "#0A5D52",
  teal: "#128B7A",
  gold: "#E8A33D",
  clay: "#C0492B",
  bg: "#F3F6F3",
  card: "#FFFFFF",
  rule: "#DCE5E0",
  muted: "#5F726C",
  good: "#0E8F62",
};

const CATEGORIES = [
  { key: "sme_credit", label: "Business loans" },
  { key: "personal_credit", label: "Personal loans" },
  { key: "corporate_credit", label: "Corporate loans" },
];

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export const revalidate = 3600;

export default async function FundingPage({
  searchParams,
}: {
  searchParams: Promise<{ type?: string; term?: string }>;
}) {
  const sp = await searchParams;
  const category = CATEGORIES.find((c) => c.key === sp.type)?.key ?? "sme_credit";
  const tenor = [1, 3, 5].includes(Number(sp.term)) ? Number(sp.term) : 1;

  const all = await getLending(category);
  if (all.length === 0) notFound();

  const rows = all
    .filter((r) => r.tenorYears === tenor)
    .sort((a, b) => (a.aprPct ?? 999) - (b.aprPct ?? 999));

  const aprs = rows.map((r) => r.aprPct).filter((v): v is number => v !== null);
  const cheapest = aprs.length ? Math.min(...aprs) : null;
  const dearest = aprs.length ? Math.max(...aprs) : null;
  const asOf = rows.find((r) => r.asOf)?.asOf ?? null;
  const label = CATEGORIES.find((c) => c.key === category)!.label;

  // How much more the dearest lender costs on a GH¢100,000 facility, per year.
  const extraOn100k =
    cheapest !== null && dearest !== null
      ? Math.round(((dearest - cheapest) / 100) * 100_000)
      : null;

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div
        className="w-full px-5 py-2 text-center text-[11px] font-medium tracking-wide text-white"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        Bank of Ghana published rates
        {asOf ? ` · ${fmtDate(asOf)}` : ""} · indicative, not quotes
      </div>

      <header className="mx-auto max-w-4xl px-5 pt-6 sm:px-8">
        <Link
          href="/"
          className="text-[19px] font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: C.deep }}
        >
          {BRAND.name}
        </Link>
      </header>

      <div className="mx-auto max-w-4xl px-5 py-8 sm:px-8 sm:py-10">
        <section
          className="overflow-hidden rounded-3xl p-7 text-white sm:p-10"
          style={{
            background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 62%, ${C.gold} 190%)`,
          }}
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-80">
            {label} · {tenor} year{tenor > 1 ? "s" : ""}
          </p>
          <h1
            className="mt-3 text-[2.1rem] font-bold leading-[1.08] sm:text-[3rem]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            The same loan,
            <br />
            three times the price.
          </h1>

          {cheapest !== null && (
            <div className="mt-8 grid grid-cols-3 gap-4 sm:max-w-lg">
              {[
                { k: "Cheapest bank", v: `${cheapest.toFixed(2)}%`, hi: true },
                { k: "Dearest bank", v: `${dearest!.toFixed(2)}%` },
                { k: "Banks compared", v: String(rows.length) },
              ].map(({ k, v, hi }) => (
                <div key={k}>
                  <p className="text-[10px] uppercase tracking-wider opacity-75">
                    {k}
                  </p>
                  <p
                    className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]"
                    style={{ color: hi ? C.gold : "#fff" }}
                  >
                    {v}
                  </p>
                </div>
              ))}
            </div>
          )}

          {extraOn100k !== null && extraOn100k > 0 && (
            <p className="mt-7 max-w-xl text-[14px] leading-relaxed opacity-90">
              On a GH&#8373;100,000 facility that difference is about{" "}
              <strong>GH&#8373;{extraOn100k.toLocaleString()}</strong> a year —
              for the same money, over the same term, from banks the same
              regulator licenses.
            </p>
          )}
        </section>

        {/* Filters. Stated criteria, not a recommendation. */}
        <nav className="mt-7 flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <Link
              key={c.key}
              href={`/funding?type=${c.key}&term=${tenor}`}
              className="rounded-full px-4 py-2 text-[13px] font-semibold"
              style={{
                background: c.key === category ? C.deep : C.card,
                color: c.key === category ? "#fff" : C.ink,
                border: `1px solid ${c.key === category ? C.deep : C.rule}`,
              }}
            >
              {c.label}
            </Link>
          ))}
        </nav>
        <nav className="mt-2 flex flex-wrap gap-2">
          {[1, 3, 5].map((t) => (
            <Link
              key={t}
              href={`/funding?type=${category}&term=${t}`}
              className="rounded-full px-4 py-1.5 text-[12.5px] font-semibold"
              style={{
                background: t === tenor ? `${C.teal}1A` : C.card,
                color: t === tenor ? C.deep : C.muted,
                border: `1px solid ${t === tenor ? C.teal : C.rule}`,
              }}
            >
              {t} year{t > 1 ? "s" : ""}
            </Link>
          ))}
        </nav>

        {/*
          Placed above the rate list, because someone who has not yet worked out
          what they need should not have to read 22 bank rows first. Someone who
          knows exactly what they want will scroll past it.
        */}
        <Link
          href="/funding/match"
          className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl px-5 py-4"
          style={{ background: `${C.gold}14`, border: `1px solid ${C.gold}` }}
        >
          <span className="text-[13.5px]">
            <strong>Not sure which of these you&rsquo;d qualify for?</strong>{" "}
            Answer nine questions and we&rsquo;ll show what each would cost you.
          </span>
          <span
            className="shrink-0 rounded-full px-4 py-2 text-[12.5px] font-bold text-white"
            style={{ background: "#7A3E12" }}
          >
            Work it out →
          </span>
        </Link>

        <p
          className="mt-5 rounded-2xl px-5 py-4 text-[13px] leading-relaxed"
          style={{ background: `${C.gold}1A` }}
        >
          <strong>These are indicative rates, not offers.</strong> Bank of Ghana
          publishes them so borrowers can compare. What any bank actually offers
          you depends on its assessment of your business — your trading history,
          security, and accounts. Treat this as where to start asking, not what
          you will pay.
        </p>

        <ol className="mt-6 space-y-3">
          {rows.map((r, i) => {
            const isCheapest = r.aprPct !== null && r.aprPct === cheapest;
            const width =
              r.aprPct !== null && cheapest !== null && dearest !== null &&
              dearest !== cheapest
                ? 14 + ((r.aprPct - cheapest) / (dearest - cheapest)) * 86
                : 100;
            return (
              <li
                key={r.id}
                className="rounded-2xl p-5"
                style={{
                  background: C.card,
                  border: `1px solid ${isCheapest ? C.gold : C.rule}`,
                }}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span
                      className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold"
                      style={{
                        background: isCheapest ? C.gold : `${C.teal}1A`,
                        color: isCheapest ? C.ink : C.deep,
                      }}
                    >
                      {i + 1}
                    </span>
                    <div className="min-w-0">
                      <h2 className="text-[15.5px] font-bold leading-snug">
                        {r.provider.name}
                      </h2>
                      <p className="mt-0.5 text-[12px]" style={{ color: C.muted }}>
                        {creditLabel(r.category)} · {r.tenorYears} year
                        {r.tenorYears > 1 ? "s" : ""}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-[1.5rem] font-bold tabular-nums leading-none">
                      {r.aprPct !== null ? `${r.aprPct.toFixed(2)}%` : "—"}
                    </p>
                    <p className="mt-0.5 text-[10.5px]" style={{ color: C.muted }}>
                      all-in cost a year
                    </p>
                  </div>
                </div>

                <div
                  className="mt-4 h-1.5 w-full overflow-hidden rounded-full"
                  style={{ background: C.rule }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${width}%`,
                      background: isCheapest
                        ? `linear-gradient(90deg, ${C.deep}, ${C.gold})`
                        : C.teal,
                    }}
                  />
                </div>

                {/* The gap is the point: fees a headline rate does not show. */}
                {r.lendingRatePct !== null && (
                  <p className="mt-3 text-[12.5px]" style={{ color: C.muted }}>
                    Advertised rate{" "}
                    <strong style={{ color: C.ink }}>
                      {r.lendingRatePct.toFixed(2)}%
                    </strong>
                    {r.feeGapPct !== null && r.feeGapPct > 0.05 ? (
                      <>
                        {" "}
                        — fees add{" "}
                        <strong style={{ color: C.clay }}>
                          {r.feeGapPct.toFixed(2)} points
                        </strong>
                        .
                      </>
                    ) : (
                      <> — no additional charges reported.</>
                    )}
                  </p>
                )}
              </li>
            );
          })}
        </ol>

        <section
          className="mt-12 rounded-3xl p-6 sm:p-8"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2
            className="text-[18px] font-bold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            What this page doesn&rsquo;t show
          </h2>
          <ul
            className="mt-4 space-y-3 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            <li>
              <strong style={{ color: C.ink }}>Whether you&rsquo;ll qualify.</strong>{" "}
              The binding question for most Ghanaian businesses isn&rsquo;t the
              rate, it&rsquo;s access. Bank capital rules make small loans
              costly to process, so many applications are refused regardless of
              the business.
            </li>
            <li>
              <strong style={{ color: C.ink }}>Anyone but banks.</strong>{" "}
              Microfinance institutions, savings and loans companies and digital
              lenders aren&rsquo;t in Bank of Ghana&rsquo;s APR report — and
              they&rsquo;re where businesses refused by banks actually borrow.
            </li>
            <li>
              <strong style={{ color: C.ink }}>Security and covenants.</strong>{" "}
              What a bank asks you to pledge can matter more than the rate.
            </li>
          </ul>
          <p className="mt-6 text-[11px] leading-relaxed" style={{ color: C.muted }}>
            {BRAND.legalStatus} We are not a credit broker and do not arrange
            finance.
          </p>
        </section>

        <p className="mt-8 text-[13px]">
          <Link
            href="/"
            className="underline underline-offset-4"
            style={{ color: C.deep }}
          >
            ← Investing side
          </Link>
        </p>
      </div>
    </main>
  );
}
