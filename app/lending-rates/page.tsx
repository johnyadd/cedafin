import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import DataProvenance from "@/components/DataProvenance";
import Footer from "@/components/Footer";
import ShareThis from "@/components/ShareThis";
import { BRAND } from "@/lib/brand";
import { getLendingHistory, type LendingHistoryRow } from "@/lib/data/funds";

/**
 * app/lending-rates/page.tsx — what Ghanaian banks charged to lend, across
 * every Bank of Ghana return held.
 *
 * WHY THIS PAGE EXISTS
 * Bank of Ghana requires every bank to report what its lending costs, fees
 * included, and publishes the result. Then it replaces it with the next
 * month's and keeps no archive. We hold the returns we captured; side by
 * side they show how borrowing costs moved, which nobody outside the Bank
 * can otherwise show.
 *
 * WHY EVERY SENTENCE IS COMPUTED
 * The summary lines are built from the data, not typed. When another return
 * loads, "fell from X to Y" and the real-rate line recalculate, and the
 * wording that depends on direction chooses itself.
 *
 * ONE ROW PER BANK, NOT PER NAME
 * Bank of Ghana renamed FBNBank (Ghana) to First Bank Ghana between June 2025
 * and May 2026. Grouping by the printed name split one bank into two
 * half-empty rows. Rows are grouped by the provider the name links to, and
 * labelled with the name the Bank used most recently.
 *
 * SNAPSHOTS, NOT A SERIES
 * The page draws no line between returns: a line implies the months in
 * between are known.
 *
 * THE REAL-RATE LINE
 * Each return's median one-year APR against headline inflation in the same
 * month, compounded rather than subtracted. Contemporaneous inflation is a
 * rough measure and the page says so.
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
  title: "Ghana bank lending rates over time — every Bank of Ghana return we hold",
  description:
    "What Ghanaian banks charged to lend, fees included, across the Bank of Ghana returns we hold — returns the Bank replaces each month and does not archive. Small business, personal and corporate credit, bank by bank.",
  keywords: [
    "Ghana lending rates history",
    "Ghana bank interest rates 2025",
    "Ghana APR by bank",
    "Bank of Ghana annual percentage rate",
    "SME loan rates Ghana",
  ],
};

export const revalidate = 3600;

const CATS: [string, string][] = [
  ["sme", "Small business"],
  ["household", "Personal"],
  ["corporate", "Corporate"],
];

function median(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function monthLabel(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function pct(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : `${v.toFixed(2)}%`;
}

export default async function LendingRatesPage() {
  const { rows, cpi } = await getLendingHistory();

  const dates = [...new Set(rows.map((r) => r.asOf))].sort();
  const first = dates[0];
  const last = dates[dates.length - 1];
  const cpiAt = new Map(cpi.map((c) => [c.asOf, c.value]));

  const oneYear = rows.filter((r) => r.tenorYears === 1 && r.apr !== null);

  const stats = (cat: string, d: string) => {
    const v = oneYear
      .filter((r) => r.category === cat && r.asOf === d)
      .map((r) => r.apr as number);
    return {
      n: v.length,
      low: v.length ? Math.min(...v) : null,
      med: median(v),
      high: v.length ? Math.max(...v) : null,
    };
  };

  const real = (nominalPct: number | null, d: string) => {
    const infl = cpiAt.get(d);
    if (nominalPct === null || infl === undefined) return null;
    return ((1 + nominalPct / 100) / (1 + infl) - 1) * 100;
  };

  const smeFirst = stats("sme", first);
  const smeLast = stats("sme", last);
  const corpFirst = stats("corporate", first);
  const corpLast = stats("corporate", last);
  const realFirst = real(smeFirst.med, first);
  const realLast = real(smeLast.med, last);

  // Bank by bank, one year, small business — grouped by the provider each
  // printed name links to, so a renamed bank stays one row.
  const smeRows = rows.filter((r) => r.category === "sme" && r.tenorYears === 1);
  const groupKey = (r: LendingHistoryRow) => r.providerSlug ?? r.bank;
  const groups = new Map<string, LendingHistoryRow[]>();
  for (const r of smeRows) {
    const k = groupKey(r);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k)!.push(r);
  }
  const bankRows = [...groups.entries()]
    .map(([k, rs]) => {
      const newest = [...rs].sort((a, b) => b.asOf.localeCompare(a.asOf))[0];
      const at = (d: string) => rs.find((r) => r.asOf === d)?.apr ?? null;
      return { key: k, label: newest.bank, slug: newest.providerSlug, at };
    })
    // A bank that never reported this cell has nothing to show here.
    .filter((b) => dates.some((d) => b.at(d) !== null))
    .sort((a, b) => (a.at(last) ?? Infinity) - (b.at(last) ?? Infinity));

  const fellOrRose = (a: number | null, b: number | null) =>
    a === null || b === null ? "moved" : b < a ? "fell" : b > a ? "rose" : "held";

  const thisMonth = new Date().toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
  });

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div className="mx-auto max-w-4xl px-5 py-10 sm:px-8 sm:py-12">
        <p
          className="text-[11px] font-semibold uppercase tracking-[0.16em]"
          style={{ color: C.gold }}
        >
          Lending rates over time
        </p>
        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.1] sm:text-[2.4rem]"
          style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.02em" }}
        >
          What Ghanaian banks charged to lend, {monthLabel(first)} to{" "}
          {monthLabel(last)}
        </h1>
        <p className="mt-5 text-[16.5px] leading-relaxed" style={{ color: C.muted }}>
          Every bank must report to Bank of Ghana what its lending costs once
          fees are counted. Bank of Ghana replaces each return with the next and
          keeps no archive, so these {dates.length} returns — the ones we
          captured — are not available together anywhere else.
        </p>

        {/* The summary, computed. */}
        <div
          className="mt-8 overflow-hidden rounded-2xl"
          style={{ background: C.card, border: `1px solid ${C.gold}` }}
        >
          <div className="flex">
            <span className="w-1 shrink-0" style={{ background: C.gold }} aria-hidden="true" />
            <div className="flex-1 p-5">
              <p className="text-[15.5px] leading-relaxed">
                The median one-year cost of a <strong>small business loan</strong>{" "}
                {fellOrRose(smeFirst.med, smeLast.med)} from{" "}
                <strong>{pct(smeFirst.med)}</strong> in {monthLabel(first)} to{" "}
                <strong>{pct(smeLast.med)}</strong> in {monthLabel(last)}. For a{" "}
                <strong>corporate borrower</strong> it{" "}
                {fellOrRose(corpFirst.med, corpLast.med)} from{" "}
                <strong>{pct(corpFirst.med)}</strong> to{" "}
                <strong>{pct(corpLast.med)}</strong>.
              </p>
              {smeFirst.med !== null &&
                smeLast.med !== null &&
                corpFirst.med !== null &&
                corpLast.med !== null && (
                  <p className="mt-3 text-[14.5px] leading-relaxed" style={{ color: C.muted }}>
                    In {monthLabel(first)} the gap between them was{" "}
                    {Math.abs(smeFirst.med - corpFirst.med).toFixed(2)} points. By{" "}
                    {monthLabel(last)} it was{" "}
                    {Math.abs(smeLast.med - corpLast.med).toFixed(2)} points.
                  </p>
                )}
              {realFirst !== null && realLast !== null && (
                <p className="mt-3 text-[14.5px] leading-relaxed" style={{ color: C.muted }}>
                  Against inflation in the same month, the median small business
                  rate was <strong style={{ color: C.ink }}>{pct(realFirst)}</strong>{" "}
                  in real terms in {monthLabel(first)} and{" "}
                  <strong style={{ color: C.ink }}>{pct(realLast)}</strong> in{" "}
                  {monthLabel(last)}.{" "}
                  {realLast > realFirst
                    ? "So although the headline rate fell, borrowing became dearer in real terms, because inflation fell faster than lending rates did."
                    : "Borrowing became cheaper in real terms as well as in headline terms."}{" "}
                  This uses inflation at the time of each return, a common rough
                  measure — not the inflation a borrower will live through over
                  the loan.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Summary table by category. */}
        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          One-year loans, by kind of borrower
        </h2>
        <p className="mt-2 text-[13.5px]" style={{ color: C.muted }}>
          Annual percentage rate, fees included, across the banks that reported
          in each return.
        </p>
        <div className="mt-4 space-y-4">
          {CATS.map(([cat, label]) => (
            <div
              key={cat}
              className="overflow-x-auto rounded-2xl"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <table className="w-full min-w-[520px] text-left text-[13.5px]">
                <caption
                  className="px-4 pt-4 text-left text-[14.5px] font-bold"
                  style={{ color: C.deep }}
                >
                  {label}
                </caption>
                <thead>
                  <tr style={{ color: C.muted }}>
                    <th className="px-4 py-2 font-semibold">Return</th>
                    <th className="px-4 py-2 font-semibold">Banks</th>
                    <th className="px-4 py-2 font-semibold">Lowest</th>
                    <th className="px-4 py-2 font-semibold">Median</th>
                    <th className="px-4 py-2 font-semibold">Highest</th>
                  </tr>
                </thead>
                <tbody>
                  {dates.map((d) => {
                    const s = stats(cat, d);
                    return (
                      <tr key={d} style={{ borderTop: `1px solid ${C.rule}` }}>
                        <td className="px-4 py-2">{monthLabel(d)}</td>
                        <td className="px-4 py-2 tabular-nums">{s.n}</td>
                        <td className="px-4 py-2 tabular-nums">{pct(s.low)}</td>
                        <td className="px-4 py-2 font-semibold tabular-nums">{pct(s.med)}</td>
                        <td className="px-4 py-2 tabular-nums">{pct(s.high)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ))}
        </div>

        {/* Bank by bank. */}
        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Bank by bank: a one-year small business loan
        </h2>
        <p className="mt-2 text-[13.5px]" style={{ color: C.muted }}>
          Ordered by the latest return, cheapest first. Banks are named as in
          Bank of Ghana&rsquo;s most recent return. A dash means the bank did
          not report that cell in that return.
        </p>
        <div
          className="mt-4 overflow-x-auto rounded-2xl"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <table className="w-full min-w-[640px] text-left text-[13px]">
            <thead>
              <tr style={{ color: C.muted }}>
                <th className="px-4 py-3 font-semibold">Bank</th>
                {dates.map((d) => (
                  <th key={d} className="px-4 py-3 font-semibold tabular-nums">
                    {monthLabel(d)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bankRows.map((b) => (
                <tr key={b.key} style={{ borderTop: `1px solid ${C.rule}` }}>
                  <td className="px-4 py-2">
                    {b.slug ? (
                      <Link
                        href={`/lenders/${b.slug}`}
                        className="underline underline-offset-4"
                        style={{ color: C.deep }}
                      >
                        {b.label}
                      </Link>
                    ) : (
                      b.label
                    )}
                  </td>
                  {dates.map((d) => (
                    <td key={d} className="px-4 py-2 tabular-nums">
                      {pct(b.at(d))}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Snapshots, not a monthly series
        </h2>
        <p className="mt-3 text-[15px] leading-relaxed">
          Bank of Ghana publishes this return monthly and replaces it with the
          next. These are the months we captured, and the months between them
          are not shown — which is why the page sets the returns side by side
          rather than drawing a line through them. The original documents are
          kept in the{" "}
          <Link href="/the-archive" className="font-semibold underline underline-offset-4" style={{ color: C.deep }}>archive</Link>.
          Today&rsquo;s rates, with every bank and term, are on{" "}
          <Link href="/funding" className="font-semibold underline underline-offset-4" style={{ color: C.deep }}>compare business credit</Link>.
        </p>

        <ShareThis
          path="/lending-rates"
          audience="somebody about to borrow in Ghana"
          message="What Ghanaian banks charged to lend, side by side across Bank of Ghana returns the Bank itself no longer keeps."
        />

        <DataProvenance
          title="Ghanaian bank lending rates over time"
          source="Bank of Ghana's Annual Percentage Rate returns"
          covering={`${dates.length} returns, ${monthLabel(first)} to ${monthLabel(last)}, every licensed bank that reported`}
          checked={thisMonth}
          method="Each return read directly from the archived Bank of Ghana PDF. Rates are annual percentage rates as the Bank published them, fees included. A cell a bank did not report is left blank. Medians are across the banks that reported in that return. Real rates use headline inflation in the same month, compounded rather than subtracted."
          pageUrl="https://cedafin.com/lending-rates"
        />

        <p className="mt-6 text-[12.5px] leading-relaxed" style={{ color: C.muted }}>
          {BRAND.legalStatus} Rates are indicative: Bank of Ghana notes that the
          APR an individual borrower is offered depends on the bank&rsquo;s
          assessment of them.
        </p>
      </div>

      <Footer />
    </main>
  );
}
