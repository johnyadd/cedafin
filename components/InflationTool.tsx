"use client";

import { useMemo, useState } from "react";

/**
 * components/InflationTool.tsx — the arithmetic, and the caveat.
 *
 * WHY IT OPENS WITH AN ANSWER
 * Same reasoning as the returns calculator: a tool that opens as an empty form
 * asks the visitor to supply something before receiving anything, and most of
 * them leave. This arrives already worked out and every figure is editable.
 *
 * THE REDENOMINATION, WHICH IS THE WHOLE DIFFICULTY
 * Ghana dropped four zeroes in July 2007 — GH₵1 replaced ¢10,000.
 *
 * The price index is continuous across that change, because an index measures
 * what things cost rather than how the notes are denominated. So the
 * arithmetic is right either way.
 *
 * But an amount from 1995 was quoted in old cedis, and someone who remembers
 * paying ¢2,000 for something will read a result in new cedis as nonsense
 * unless told. The tool shows the answer in both, for any year before 2007,
 * rather than picking one and hoping.
 */

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  teal: "#1B8BC0",
  gold: "#E8A33D",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
  good: "#0E8F62",
};

/** July 2007: GH₵1 replaced ¢10,000. */
const REDENOMINATION_YEAR = 2007;
const REDENOMINATION_FACTOR = 10_000;

export default function InflationTool({
  index,
}: {
  index: { year: number; value: number }[];
}) {
  const years = index.map((r) => r.year);
  const latest = years.length ? Math.max(...years) : 2025;
  const earliest = years.length ? Math.min(...years) : 1964;

  const [amount, setAmount] = useState("100");
  const [from, setFrom] = useState(String(Math.max(earliest, 2010)));
  const [to, setTo] = useState(String(latest));

  const lookup = useMemo(
    () => new Map(index.map((r) => [r.year, r.value])),
    [index],
  );

  const r = useMemo(() => {
    const amt = Number(amount) || 0;
    const y1 = Number(from);
    const y2 = Number(to);
    const i1 = lookup.get(y1);
    const i2 = lookup.get(y2);
    if (!i1 || !i2) return null;

    const ratio = i2 / i1;
    const equivalent = amt * ratio;
    const totalPct = (ratio - 1) * 100;
    const yearsApart = Math.abs(y2 - y1);
    // Compound annual rate, which is the honest way to express an average over
    // a long span — the arithmetic mean of annual rates would overstate it.
    const annualPct =
      yearsApart > 0 ? (Math.pow(ratio, 1 / yearsApart) - 1) * 100 : 0;

    return {
      amt,
      y1,
      y2,
      equivalent,
      totalPct,
      annualPct,
      yearsApart,
      // Only relevant when the earlier year predates July 2007.
      spansRedenomination: y1 < REDENOMINATION_YEAR,
      oldCedis: amt * REDENOMINATION_FACTOR,
    };
  }, [amount, from, to, lookup]);

  const money = (v: number) =>
    `GH₵${v.toLocaleString("en-GB", { maximumFractionDigits: 2 })}`;

  const selectStyle = {
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
          What is it worth now?
        </h2>
      </div>

      <div className="p-5 sm:p-6">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
          <label className="block">
            <span
              className="text-[11px] font-semibold uppercase tracking-[0.12em]"
              style={{ color: C.muted }}
            >
              Amount in cedis
            </span>
            <input
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="mt-1.5 w-full rounded-xl px-3 py-2.5 text-[15px] tabular-nums"
              style={selectStyle}
            />
          </label>

          <label className="block">
            <span
              className="text-[11px] font-semibold uppercase tracking-[0.12em]"
              style={{ color: C.muted }}
            >
              In
            </span>
            <select
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              className="mt-1.5 w-full cursor-pointer rounded-xl px-3 py-2.5 text-[15px]"
              style={selectStyle}
            >
              {years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span
              className="text-[11px] font-semibold uppercase tracking-[0.12em]"
              style={{ color: C.muted }}
            >
              Is worth, in
            </span>
            <select
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="mt-1.5 w-full cursor-pointer rounded-xl px-3 py-2.5 text-[15px]"
              style={selectStyle}
            >
              {years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </label>
        </div>

        {r ? (
          <>
            <div
              className="mt-5 rounded-2xl p-5 text-white"
              style={{
                background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 72%)`,
              }}
            >
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] opacity-80">
                {money(r.amt)} in {r.y1} has the buying power of
              </p>
              <p
                className="mt-1.5 text-[2rem] font-bold tabular-nums leading-none sm:text-[2.6rem]"
                style={{ color: C.gold }}
              >
                {money(r.equivalent)}
              </p>
              <p className="mt-1.5 text-[13px] opacity-90">
                in {r.y2} — prices rose {r.totalPct.toFixed(1)}% over{" "}
                {r.yearsApart} {r.yearsApart === 1 ? "year" : "years"}
                {r.yearsApart > 1 && (
                  <>, an average of {r.annualPct.toFixed(1)}% a year</>
                )}
              </p>
            </div>

            {r.spansRedenomination && (
              <div
                className="mt-3 rounded-2xl p-4 text-[12.5px] leading-relaxed"
                style={{
                  background: C.card,
                  border: `1px solid ${C.gold}`,
                  color: C.muted,
                }}
              >
                <strong style={{ color: C.ink }}>
                  About the old cedi.
                </strong>{" "}
                Ghana dropped four zeroes in July 2007 — GH₵1 replaced ¢10,000.
                So {money(r.amt)} in {r.y1} would have been written as{" "}
                <strong style={{ color: C.ink }}>
                  ¢{r.oldCedis.toLocaleString("en-GB")}
                </strong>{" "}
                at the time.
                <br />
                <br />
                The calculation above is still correct: a price index measures
                what things cost, not how the notes are denominated, so it runs
                continuously across the change.
              </div>
            )}
          </>
        ) : (
          <p className="mt-5 text-[14px]" style={{ color: C.muted }}>
            No index figure for one of those years.
          </p>
        )}

        <p className="mt-4 text-[11.5px]" style={{ color: C.muted }}>
          Annual index, {earliest} to {latest}. Ghana&rsquo;s consumer price
          index, 2010 = 100.
        </p>
      </div>
    </div>
  );
}
