"use client";

import { useMemo, useState } from "react";

/**
 * components/TbillTool.tsx — both directions, because only one of them is
 * the question people actually have.
 *
 * WHY THIS EXISTS AT ALL
 * The first version of this idea was rejected, correctly: "what does GH₵1,000
 * become" is arithmetic anybody can do, and a calculator for it adds nothing.
 *
 * The useful question is the reverse. A business owes GH₵15,000 to a supplier
 * in three months and has the money now. What do they put into a bill today?
 * That is how a Treasury bill is actually used — a known obligation on a known
 * date — and working backwards from the face value is the calculation people
 * get wrong.
 *
 * So this opens in the "I need" direction, with "I have" as the alternative.
 *
 * THE MATHS
 * A Ghanaian Treasury bill is a discount instrument. You pay less than the
 * face value and receive the face value at maturity; the difference is the
 * return. Bank of Ghana publishes both a discount rate and an interest rate
 * for each tenor, and they are not the same number — the interest rate is the
 * yield on what you actually pay, which is what a saver wants.
 *
 *   price = face / (1 + rate × days/365)
 *
 * We use the interest rate, and say so, because using the discount rate would
 * understate what a buyer earns.
 *
 * THE CAVEAT THAT MATTERS
 * The rate is set at auction, weekly. Today's figure tells you what the last
 * auction cleared at, not what yours will. The answer is indicative and the
 * tool says so rather than implying a guarantee.
 */

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  teal: "#1B8BC0",
  gold: "#E8A33D",
  clay: "#C0492B",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  bg: "#F2F6F9",
  muted: "#5F6E78",
};

export interface TbillRate {
  days: number;
  label: string;
  ratePct: number;
  asOf: string | null;
}

type Direction = "need" | "have";

export default function TbillTool({
  rates,
  inflationPct,
}: {
  rates: TbillRate[];
  inflationPct: number | null;
}) {
  const [direction, setDirection] = useState<Direction>("need");
  const [amount, setAmount] = useState("15000");
  const [days, setDays] = useState(rates[0]?.days ?? 91);

  const rate = useMemo(
    () => rates.find((r) => r.days === days) ?? rates[0] ?? null,
    [rates, days],
  );

  const r = useMemo(() => {
    const amt = Number(amount) || 0;
    if (!amt || !rate) return null;

    const factor = 1 + (rate.ratePct / 100) * (rate.days / 365);

    // "need": amount is the face value, solve for the price.
    // "have": amount is the price, solve for the face value.
    const price = direction === "need" ? amt / factor : amt;
    const face = direction === "need" ? amt : amt * factor;

    // Fisher over the holding period, not annualised — comparing a 91-day
    // return against an annual inflation rate would overstate the loss.
    const periodInflation = inflationPct
      ? Math.pow(1 + inflationPct / 100, rate.days / 365) - 1
      : null;
    const periodReturn = factor - 1;
    const realPct =
      periodInflation === null
        ? null
        : ((1 + periodReturn) / (1 + periodInflation) - 1) * 100;

    return {
      price,
      face,
      earned: face - price,
      earnedPct: (face - price) / price * 100,
      realPct,
      periodReturnPct: periodReturn * 100,
    };
  }, [amount, direction, rate, inflationPct]);

  const money = (v: number) =>
    `GH₵${v.toLocaleString("en-GB", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;

  const inputStyle = {
    border: `1px solid ${C.rule}`,
    background: C.card,
    color: C.ink,
  };

  return (
    <div
      className="overflow-hidden rounded-3xl"
      style={{ background: C.card, border: `1px solid ${C.rule}` }}
    >
      <div
        className="px-5 py-3.5 text-white sm:px-6"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        <h2
          className="text-[15px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Treasury bill calculator
        </h2>
      </div>

      <div className="p-5 sm:p-6">
        {/* Direction first — it changes what the amount field means. */}
        <div
          className="inline-flex rounded-full p-1"
          style={{ background: C.bg, border: `1px solid ${C.rule}` }}
        >
          {(
            [
              ["need", "I need an amount on a date"],
              ["have", "I have an amount to invest"],
            ] as [Direction, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setDirection(key)}
              className="rounded-full px-3.5 py-1.5 text-[12.5px] font-semibold transition-colors"
              style={
                direction === key
                  ? { background: C.deep, color: "#fff" }
                  : { color: C.muted }
              }
            >
              {label}
            </button>
          ))}
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span
              className="text-[11px] font-semibold uppercase tracking-[0.12em]"
              style={{ color: C.muted }}
            >
              {direction === "need"
                ? "Amount you need, GH₵"
                : "Amount you have, GH₵"}
            </span>
            <input
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="mt-1.5 w-full rounded-xl px-3 py-2.5 text-[15px] tabular-nums"
              style={inputStyle}
            />
          </label>

          {/*
            Tenor as buttons, and the rate taken out of them.

            The dropdown read "91 days — 4.75%", which bundles a choice with a
            figure. Picking a term and knowing today rate are different
            questions, and the second belongs below as a stated fact with its
            date — which also gives the auction caveat somewhere to sit.
          */}
          <div className="block">
            <span
              className="text-[11px] font-semibold uppercase tracking-[0.12em]"
              style={{ color: C.muted }}
            >
              How long
            </span>
            <div className="mt-1.5 grid grid-cols-3 gap-2">
              {rates.map((t) => (
                <button
                  key={t.days}
                  type="button"
                  onClick={() => setDays(t.days)}
                  className="rounded-xl px-2 py-2.5 text-[14px] font-semibold transition-colors"
                  style={
                    days === t.days
                      ? { background: C.deep, color: "#fff", border: `1px solid ${C.deep}` }
                      : { background: C.card, color: C.ink, border: `1px solid ${C.rule}` }
                  }
                >
                  {t.days} days
                </button>
              ))}
            </div>
          </div>
        </div>

        {rate && (
          <p
            className="mt-3 text-[13px] leading-relaxed"
            style={{ color: C.muted }}
          >
            The {rate.days}-day bill last cleared at{" "}
            <strong style={{ color: C.ink }}>{rate.ratePct.toFixed(2)}%</strong>
            {rate.asOf ? ` at the auction on ${rate.asOf}` : ""}. Rates are set
            weekly, so yours will be whatever the next auction clears at.
          </p>
        )}

        {r && rate ? (
          <>
            <div
              className="mt-5 rounded-2xl p-5"
              style={{
                background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 72%)`,
              }}
            >
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white opacity-80">
                {direction === "need"
                  ? `To have ${money(r.face)} in ${rate.days} days, buy`
                  : `${money(r.price)} over ${rate.days} days returns`}
              </p>
              <p
                className="mt-1.5 text-[2rem] font-bold tabular-nums leading-none sm:text-[2.5rem]"
                style={{ color: C.gold }}
              >
                {money(direction === "need" ? r.price : r.face)}
              </p>
              <p className="mt-1.5 text-[13px] text-white opacity-90">
                {money(r.earned)} earned over the period —{" "}
                {r.periodReturnPct.toFixed(2)}% on what you put in, at an
                annual rate of {rate.ratePct.toFixed(2)}%
              </p>

              {r.realPct !== null && (
                <div
                  className="mt-4 border-t pt-3.5"
                  style={{ borderColor: "rgba(255,255,255,0.25)" }}
                >
                  <p className="text-[9.5px] uppercase tracking-wider text-white opacity-75">
                    After inflation
                  </p>
                  <p
                    className="mt-1 text-[1.15rem] font-bold tabular-nums leading-none"
                    style={{ color: r.realPct < 0 ? "#FFB4A2" : "#8FE3BC" }}
                  >
                    {r.realPct >= 0 ? "+" : ""}
                    {r.realPct.toFixed(2)}% over {rate.days} days
                  </p>
                  <p className="mt-1 text-[11px] text-white opacity-70">
                    {r.realPct < 0
                      ? "This bill loses purchasing power. The money comes back larger and buys less."
                      : "What the money will actually buy, after prices rise."}
                  </p>
                </div>
              )}
            </div>

            <p className="mt-3 text-[12px] leading-relaxed" style={{ color: C.muted }}>
              <strong style={{ color: C.ink }}>Indicative, not a quote.</strong>{" "}
              Treasury bill rates are set weekly at auction. The{" "}
              {rate.ratePct.toFixed(2)}% above is what the last one cleared at
              {rate.asOf ? ` (${rate.asOf})` : ""}, not what yours will. And a
              bank or broker may charge a fee on top — one Ghanaian bank
              publishes a processing fee of up to 2.5%.
            </p>
          </>
        ) : (
          <p className="mt-5 text-[14px]" style={{ color: C.muted }}>
            Enter an amount to see the figures.
          </p>
        )}
      </div>
    </div>
  );
}
