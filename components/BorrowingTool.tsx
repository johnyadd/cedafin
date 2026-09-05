"use client";

import { useMemo, useState } from "react";

/**
 * components/BorrowingTool.tsx — what a loan actually costs, at a named bank.
 *
 * WHY THE BANK SELECTOR
 * A first version defaulted to 18.00%, which I had picked as "roughly
 * typical". It was not any bank's rate and was not sourced to anything — on a
 * site whose whole argument is that figures should be traceable.
 *
 * The real median across 22 banks is 20.24% for one-year SME credit. So the
 * default is that, and every individual bank is selectable, because "GH₵9,926
 * a month" means something different once it has a name attached.
 *
 * WHY THE APR STAYS EDITABLE AFTER SELECTING
 * Bank of Ghana's figures are averages across each bank's whole book. What a
 * particular borrower is offered depends on their trading history, security
 * and accounts. Selecting a bank fills the field; it does not lock it.
 *
 * THE REAL COST, WHICH CUTS THE OTHER WAY FROM SAVINGS
 * On the savings side inflation eats a return. On the borrowing side it does
 * the opposite — you repay in cedis worth less than the ones you borrowed. At
 * 5% inflation an 11.03% loan costs about 5.7% in real terms.
 *
 * Not a reason to borrow, and not presented as one. But it is part of the true
 * cost and it is missing from every Ghanaian lending page we have seen.
 */

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  gold: "#E8A33D",
  clay: "#C0492B",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
  brownDeep: "#6B3A16",
  brownLight: "#A9662E",
};

export interface LoanOption {
  bank: string;
  category: string;
  tenorYears: number;
  aprPct: number;
}

const CATEGORY_LABELS: Record<string, string> = {
  sme_credit: "Business",
  personal_credit: "Personal",
  corporate_credit: "Corporate",
};

/** Monthly rest, which is what Ghanaian term loans use. */
function monthlyPayment(principal: number, aprPct: number, years: number) {
  const i = aprPct / 100 / 12;
  const n = Math.max(1, Math.round(years * 12));
  if (i === 0) return principal / n;
  return (principal * i) / (1 - Math.pow(1 + i, -n));
}

function median(values: number[]): number {
  if (!values.length) return 0;
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

export default function BorrowingTool({ options }: { options: LoanOption[] }) {
  const categories = useMemo(
    () => [...new Set(options.map((o) => o.category))].sort(),
    [options],
  );

  const [category, setCategory] = useState(
    categories.includes("sme_credit") ? "sme_credit" : categories[0] ?? "",
  );
  const [tenor, setTenor] = useState(1);
  const [amount, setAmount] = useState("100000");
  const [bank, setBank] = useState("");
  const [aprPct, setAprPct] = useState("");
  const [years, setYears] = useState("1");
  const [inflationPct, setInflationPct] = useState("5.0");

  /** Every bank offering the selected type and term, cheapest first. */
  const peers = useMemo(
    () =>
      options
        .filter((o) => o.category === category && o.tenorYears === tenor)
        .sort((a, b) => a.aprPct - b.aprPct),
    [options, category, tenor],
  );

  const marketMedian = useMemo(
    () => median(peers.map((p) => p.aprPct)),
    [peers],
  );

  // The APR field follows the selection until the visitor types their own.
  const effectiveApr = aprPct !== "" ? Number(aprPct) : marketMedian;

  const r = useMemo(() => {
    const p = Number(amount) || 0;
    const apr = effectiveApr || 0;
    const y = Math.max(0.25, Number(years) || 1);
    const inf = (Number(inflationPct) || 0) / 100;
    if (!p || !peers.length) return null;

    const months = Math.max(1, Math.round(y * 12));
    const monthly = monthlyPayment(p, apr, y);
    const total = monthly * months;

    const cheapest = peers[0];
    const dearest = peers[peers.length - 1];
    const cheapTotal = monthlyPayment(p, cheapest.aprPct, y) * months;
    const dearTotal = monthlyPayment(p, dearest.aprPct, y) * months;

    return {
      p,
      apr,
      y,
      monthly,
      total,
      interest: total - p,
      interestPct: ((total - p) / p) * 100,
      cheapest,
      dearest,
      cheapTotal,
      dearTotal,
      vsCheapest: total - cheapTotal,
      // Fisher, in the borrower's direction.
      realAprPct: ((1 + apr / 100) / (1 + inf) - 1) * 100,
      inflationPct: inf * 100,
      banks: peers.length,
    };
  }, [amount, effectiveApr, years, inflationPct, peers]);

  const money = (v: number) => `GH₵${Math.round(v).toLocaleString("en-GB")}`;

  const inputStyle = {
    border: `1px solid ${C.rule}`,
    background: C.card,
    color: C.ink,
  };

  /** Selecting a bank fills the APR; it does not lock it. */
  function pickBank(name: string) {
    setBank(name);
    const found = peers.find((p) => p.bank === name);
    if (found) setAprPct(found.aprPct.toFixed(2));
  }

  /** Changing type or term invalidates the bank and its rate. */
  function changeScope(nextCategory: string, nextTenor: number) {
    setCategory(nextCategory);
    setTenor(nextTenor);
    setBank("");
    setAprPct("");
    setYears(String(nextTenor));
  }

  return (
    <div
      className="overflow-hidden rounded-3xl"
      style={{ background: C.card, border: `1px solid ${C.rule}` }}
    >
      <div
        className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-5 py-3.5 text-white sm:px-6"
        style={{
          background: `linear-gradient(90deg, ${C.brownDeep}, ${C.brownLight})`,
        }}
      >
        <h2
          className="text-[15px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Loan cost calculator
        </h2>
        <p className="text-[11.5px] opacity-80">
          Pick a bank, or enter the rate you have been offered
        </p>
      </div>

      <div className="p-4 sm:p-5">
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)] lg:items-start">
          {/* Result first on mobile, right on desktop. */}
          <div className="order-1 lg:order-2">
            {r ? (
              <>
                <section
                  className="overflow-hidden rounded-2xl p-5 text-white sm:p-6"
                  style={{
                    background: `linear-gradient(135deg, ${C.brownDeep} 0%, ${C.brownLight} 75%)`,
                  }}
                >
                  <p className="text-[10px] font-semibold uppercase tracking-[0.14em] opacity-80">
                    {money(r.p)} at {r.apr.toFixed(2)}% over {r.y}{" "}
                    {r.y === 1 ? "year" : "years"}
                    {bank ? ` · ${bank}` : ""}
                  </p>
                  <p
                    className="mt-1.5 text-[2rem] font-bold tabular-nums leading-none sm:text-[2.4rem]"
                    style={{ color: C.gold }}
                  >
                    {money(r.monthly)}
                    <span className="text-[1rem] font-semibold"> /month</span>
                  </p>
                  <p className="mt-1.5 text-[13px] opacity-90">
                    {money(r.total)} in total — {money(r.interest)} of it
                    interest and fees
                  </p>

                  <div
                    className="mt-4 grid grid-cols-2 gap-4 border-t pt-3.5"
                    style={{ borderColor: "rgba(255,255,255,0.25)" }}
                  >
                    <div>
                      <p className="text-[9.5px] uppercase tracking-wider opacity-75">
                        Interest as % of the loan
                      </p>
                      <p className="mt-1 text-[1.05rem] font-bold tabular-nums leading-none sm:text-[1.25rem]">
                        {r.interestPct.toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-[9.5px] uppercase tracking-wider opacity-75">
                        Real cost after inflation
                      </p>
                      <p
                        className="mt-1 text-[1.05rem] font-bold tabular-nums leading-none sm:text-[1.25rem]"
                        style={{ color: "#8FE3BC" }}
                      >
                        {r.realAprPct.toFixed(2)}%
                      </p>
                      <p className="mt-1 text-[10px] opacity-70">
                        at {r.inflationPct.toFixed(1)}% inflation
                      </p>
                    </div>
                  </div>
                </section>

                <div
                  className="mt-3 rounded-2xl p-4"
                  style={{ background: C.card, border: `1px solid ${C.rule}` }}
                >
                  <p
                    className="text-[10px] font-semibold uppercase tracking-[0.12em]"
                    style={{ color: C.muted }}
                  >
                    The same loan across {r.banks} banks
                  </p>
                  <ul className="mt-2 space-y-1.5 text-[12.5px]">
                    <li className="flex items-baseline justify-between gap-3">
                      <span style={{ color: C.muted }}>
                        {r.cheapest.bank} ({r.cheapest.aprPct.toFixed(2)}%)
                      </span>
                      <strong className="tabular-nums">
                        {money(r.cheapTotal)}
                      </strong>
                    </li>
                    <li className="flex items-baseline justify-between gap-3">
                      <span style={{ color: C.muted }}>Your figure</span>
                      <strong className="tabular-nums">{money(r.total)}</strong>
                    </li>
                    <li className="flex items-baseline justify-between gap-3">
                      <span style={{ color: C.muted }}>
                        {r.dearest.bank} ({r.dearest.aprPct.toFixed(2)}%)
                      </span>
                      <strong className="tabular-nums">
                        {money(r.dearTotal)}
                      </strong>
                    </li>
                  </ul>
                  <p
                    className="mt-2.5 border-t pt-2.5 text-[12px] leading-relaxed"
                    style={{ borderColor: C.rule, color: C.muted }}
                  >
                    {r.vsCheapest > 500 ? (
                      <>
                        At {r.cheapest.bank}&rsquo;s reported rate this would
                        cost{" "}
                        <strong style={{ color: C.clay }}>
                          {money(r.vsCheapest)} less
                        </strong>
                        . Worth asking more than one bank.
                      </>
                    ) : (
                      <>
                        That is at or near the cheapest rate reported to Bank of
                        Ghana for this kind of borrowing.
                      </>
                    )}
                  </p>
                </div>
              </>
            ) : (
              <section
                className="rounded-2xl p-5 text-[14px]"
                style={{
                  background: C.card,
                  border: `1px solid ${C.gold}`,
                  color: C.muted,
                }}
              >
                Enter an amount to see what it would cost.
              </section>
            )}
          </div>

          {/* Form. */}
          <section
            className="order-2 rounded-2xl p-5 sm:p-6 lg:order-1"
            style={{ background: C.card, border: `1px solid ${C.rule}` }}
          >
            <h3 className="text-[14px] font-bold">Loan form</h3>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span
                  className="text-[11px] font-semibold uppercase tracking-[0.12em]"
                  style={{ color: C.muted }}
                >
                  Kind of credit
                </span>
                <select
                  value={category}
                  onChange={(e) => changeScope(e.target.value, tenor)}
                  className="mt-1.5 w-full min-w-0 cursor-pointer rounded-xl px-3 py-2.5 text-[14px]"
                  style={inputStyle}
                >
                  {categories.map((c) => (
                    <option key={c} value={c}>
                      {CATEGORY_LABELS[c] ?? c}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span
                  className="text-[11px] font-semibold uppercase tracking-[0.12em]"
                  style={{ color: C.muted }}
                >
                  Term
                </span>
                <select
                  value={tenor}
                  onChange={(e) => changeScope(category, Number(e.target.value))}
                  className="mt-1.5 w-full min-w-0 cursor-pointer rounded-xl px-3 py-2.5 text-[14px]"
                  style={inputStyle}
                >
                  {[1, 3, 5].map((t) => (
                    <option key={t} value={t}>
                      {t} year{t === 1 ? "" : "s"}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block sm:col-span-2">
                <span
                  className="text-[11px] font-semibold uppercase tracking-[0.12em]"
                  style={{ color: C.muted }}
                >
                  Bank
                </span>
                <select
                  value={bank}
                  onChange={(e) => pickBank(e.target.value)}
                  className="mt-1.5 w-full min-w-0 cursor-pointer rounded-xl px-3 py-2.5 text-[14px]"
                  style={inputStyle}
                >
                  <option value="">
                    Market median — {marketMedian.toFixed(2)}%
                  </option>
                  {peers.map((p) => (
                    <option key={p.bank} value={p.bank}>
                      {p.bank} — {p.aprPct.toFixed(2)}%
                    </option>
                  ))}
                </select>
                <span
                  className="mt-1 block text-[11px]"
                  style={{ color: C.muted }}
                >
                  Each figure is that bank&rsquo;s interest rate with its fees
                  included, reported to Bank of Ghana as an average across the
                  whole book, May 2026. What you are offered depends on your
                  circumstances.
                </span>
              </label>

              <label className="block">
                <span
                  className="text-[11px] font-semibold uppercase tracking-[0.12em]"
                  style={{ color: C.muted }}
                >
                  Amount, GH₵
                </span>
                <input
                  inputMode="decimal"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="mt-1.5 w-full rounded-xl px-3 py-2.5 text-[14px] tabular-nums"
                  style={inputStyle}
                />
              </label>

              <label className="block">
                <span
                  className="text-[11px] font-semibold uppercase tracking-[0.12em]"
                  style={{ color: C.muted }}
                >
                  Interest + fees = APR, %
                </span>
                <input
                  inputMode="decimal"
                  value={aprPct}
                  placeholder={marketMedian.toFixed(2)}
                  onChange={(e) => {
                    setAprPct(e.target.value);
                    setBank("");
                  }}
                  className="mt-1.5 w-full rounded-xl px-3 py-2.5 text-[14px] tabular-nums"
                  style={inputStyle}
                />
                <span
                  className="mt-1 block text-[11px]"
                  style={{ color: C.muted }}
                >
                  The rate on the poster plus every charge, as one annual
                  figure. One Ghanaian bank advertises 13.70% and adds 9.72
                  points of fees — an APR of 23.42%. If you have an offer, ask
                  for its APR and enter that.
                </span>
              </label>

              <label className="block">
                <span
                  className="text-[11px] font-semibold uppercase tracking-[0.12em]"
                  style={{ color: C.muted }}
                >
                  Years
                </span>
                <input
                  inputMode="decimal"
                  value={years}
                  onChange={(e) => setYears(e.target.value)}
                  className="mt-1.5 w-full rounded-xl px-3 py-2.5 text-[14px] tabular-nums"
                  style={inputStyle}
                />
              </label>

              <label className="block">
                <span
                  className="text-[11px] font-semibold uppercase tracking-[0.12em]"
                  style={{ color: C.muted }}
                >
                  Inflation, %
                </span>
                <input
                  inputMode="decimal"
                  value={inflationPct}
                  onChange={(e) => setInflationPct(e.target.value)}
                  className="mt-1.5 w-full rounded-xl px-3 py-2.5 text-[14px] tabular-nums"
                  style={inputStyle}
                />
                <span
                  className="mt-1 block text-[11px]"
                  style={{ color: C.muted }}
                >
                  5.0% is the latest Ghanaian figure, August 2026. Inflation
                  works in a borrower&rsquo;s favour — you repay in cedis worth
                  less than the ones you borrowed.
                </span>
              </label>
            </div>

            <p
              className="mt-4 text-[12px] leading-relaxed"
              style={{ color: C.muted }}
            >
              Assumes equal monthly repayments over the term. A loan with a
              different structure — interest-only, a balloon, or irregular
              drawdown — will not match this.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
