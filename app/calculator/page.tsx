"use client";

/**
 * app/calculator/page.tsx — what the fund did, what the currency did, and what
 * the charges took.
 *
 * WHY IT OPENS WITH AN ANSWER
 * A calculator that opens as an empty form asks the visitor to supply
 * information before receiving any, and most of them leave. This one arrives
 * already worked out — a real amount, a real fund, a real period, a result and
 * its breakdown. Every figure in it is editable, so adjusting it is the first
 * thing you do rather than the fourth.
 *
 * That also removes the need to choose a mode. Leave the return as the
 * historical figure and it answers "what would have happened". Type your own
 * and it answers "what if". Nobody has to pick.
 *
 * WHY THE USER ENTERS THE EXCHANGE RATES
 * We hold USD/GHS from Bank of Ghana's gold circulars and nothing else, so a
 * GBP or EUR series is not available to us. But asking is better than looking
 * it up would have been: the published mid-rate is not what anyone receives.
 * A remittance provider's margin is frequently larger than a fund's annual
 * charge, and someone who has actually sent money knows the rate they got.
 * That is the true figure, and no published source contains it.
 *
 * WHAT IT WILL NOT DO
 * Predict. Every output is arithmetic on numbers the visitor can see and
 * change. Where a return is pre-filled from a fund's published history, it says
 * so and says when. A calculator that produced a forecast would be making a
 * personal recommendation, which needs an SEC licence this site does not have.
 */

import Link from "next/link";
import { useMemo, useState } from "react";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";

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
  good: "#0E8F62",
};

/**
 * Funds we hold complete figures for. Returns are what each published, over
 * the window stated — not forecasts, and the page says so beside them.
 */
const OPTIONS: {
  id: string;
  name: string;
  chargePct: number;
  returnPct: number;
  window: string;
  note: string;
}[] = [
  {
    id: "faif",
    name: "First Atlantic Income Fund",
    chargePct: 1.75,
    returnPct: 34.73,
    window: "1 year to Jun 2026",
    note: "Cheapest annual charge of the funds we can verify.",
  },
  {
    id: "sift",
    name: "Stanbic Income Fund Trust",
    chargePct: 2.25,
    returnPct: 38.8,
    window: "1 year to Jun 2026",
    note: "Highest published return of the funds we can verify.",
  },
  {
    id: "sct",
    name: "Stanbic Cash Trust",
    chargePct: 2.25,
    returnPct: 33.62,
    window: "1 year to Jun 2026",
    note: "Money market. Takes GH₵20 to open.",
  },
  {
    id: "tbill364",
    name: "364-day Treasury bill",
    chargePct: 0,
    returnPct: 11.59,
    window: "rate at Aug 2026",
    note: "No management charge. Your bank takes something to buy it.",
  },
  {
    id: "tbill91",
    name: "91-day Treasury bill",
    chargePct: 0,
    returnPct: 5.08,
    window: "rate at Aug 2026",
    note: "Rate as at August 2026. These move weekly.",
  },
];

const CURRENCIES = [
  { code: "GBP", symbol: "£", label: "Pounds" },
  { code: "USD", symbol: "$", label: "Dollars" },
  { code: "EUR", symbol: "€", label: "Euros" },
  { code: "CAD", symbol: "C$", label: "Canadian dollars" },
];

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span
        className="text-[11px] font-semibold uppercase tracking-[0.12em]"
        style={{ color: C.muted }}
      >
        {label}
      </span>
      <div className="mt-1.5">{children}</div>
      {hint && (
        <span className="mt-1 block text-[11px]" style={{ color: C.muted }}>
          {hint}
        </span>
      )}
    </label>
  );
}

export default function CalculatorPage() {
  const [amount, setAmount] = useState("1000");
  const [ccy, setCcy] = useState("GBP");
  const [fundId, setFundId] = useState("faif");
  const [rateOut, setRateOut] = useState("15.20");
  const [rateBack, setRateBack] = useState("14.50");
  const [years, setYears] = useState("1");
  const [returnPct, setReturnPct] = useState("34.73");
  const [touchedReturn, setTouchedReturn] = useState(false);

  const fund = OPTIONS.find((f) => f.id === fundId) ?? OPTIONS[0];
  const cur = CURRENCIES.find((c) => c.code === ccy) ?? CURRENCIES[0];

  const r = useMemo(() => {
    const amt = Number(amount) || 0;
    const out = Number(rateOut) || 0;
    const back = Number(rateBack) || 0;
    const yrs = Math.max(0.25, Number(years) || 1);
    const ret = (Number(returnPct) || 0) / 100;
    const chg = fund.chargePct / 100;

    // Returning null here made the whole card vanish the moment someone
    // cleared a field to type a new number — the layout jumped and the result
    // they were watching disappeared. Better to show zeros and let it fill in
    // as they type.
    if (!out || !back) return null;

    const cedisIn = amt * out;
    // Return compounds over the period; the charge is taken annually from the
    // value, so it compounds against you over the same period.
    const grossOut = cedisIn * Math.pow(1 + ret, yrs);
    const netOut = grossOut * Math.pow(1 - chg, yrs);
    const chargeCost = grossOut - netOut;
    const homeBack = netOut / back;

    // Splitting the outcome three ways. The fund's contribution is measured in
    // cedis and converted at the ORIGINAL rate, so the currency line carries
    // the whole exchange effect rather than smearing it across the others.
    const fundGainHome = (grossOut - cedisIn) / out;
    const chargeCostHome = chargeCost / out;
    const currencyEffect = homeBack - amt - fundGainHome + chargeCostHome;

    return {
      amt,
      cedisIn,
      grossOut,
      netOut,
      homeBack,
      totalGain: homeBack - amt,
      // Zero divided by zero is NaN, which appeared on screen the moment
      // someone cleared the amount to type a new one.
      totalPct: amt > 0 ? ((homeBack / amt) - 1) * 100 : 0,
      fundGainHome,
      chargeCostHome,
      currencyEffect,
      fundOnlyPct: ret * 100,
    };
  }, [amount, rateOut, rateBack, years, returnPct, fund]);

  const money = (v: number) =>
    `${cur.symbol}${Math.abs(v).toLocaleString("en-GB", {
      maximumFractionDigits: 0,
    })}`;

  const inputStyle = {
    border: `1px solid ${C.rule}`,
    background: C.card,
    color: C.ink,
  };

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div className="mx-auto max-w-4xl px-5 py-6 sm:px-8">
        {/*
          Deliberately small. The heading and intro were taking a third of the
          screen before anything useful appeared, which pushed the result out of
          view — and the sticky version that fixed that covered the form
          instead. Shrinking both is the answer that costs nothing.
        */}
        <h1
          className="text-[1.5rem] font-bold leading-[1.15] sm:text-[1.8rem]"
          style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.015em" }}
        >
          What the fund did, what the currency did, and what it cost
        </h1>
        <p
          className="mt-2 max-w-2xl text-[13.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          Sending money to Ghana from abroad? The exchange rate usually moves
          your outcome more than the fund does. This separates the two.
        </p>

        {/*
          The answer, before anything is asked — and it follows you down the
          page.

          The value of this tool is not seeing a result once. It is watching
          the number move when you change a rate, which you cannot do if the
          result has scrolled off the top by the time you reach the input.

          The header is already sticky at 0, so this sits below it.
        */}
        {r && (
          <section
            className="mt-6 overflow-hidden rounded-2xl p-5 text-white sm:p-6"
            style={{
              background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 72%)`,
            }}
          >
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] opacity-80">
              {money(r.amt)} in {fund.name}, over {years}{" "}
              {Number(years) === 1 ? "year" : "years"}
            </p>
            <p
              className="mt-1.5 text-[1.9rem] font-bold tabular-nums leading-none sm:text-[2.4rem]"
              style={{ color: r.totalGain >= 0 ? C.gold : "#FFC9BC" }}
            >
              {money(r.homeBack)}
            </p>
            <p className="mt-1.5 text-[13px] opacity-90">
              {r.totalGain >= 0 ? "Up" : "Down"} {money(r.totalGain)} —{" "}
              {r.totalPct >= 0 ? "+" : ""}
              {r.totalPct.toFixed(1)}% on what you sent
            </p>
            {/* Both currencies. Someone sending money abroad thinks in two,
                and seeing only one hides where the money actually went. */}
            <p className="mt-0.5 text-[11px] opacity-70">
              GH₵{Math.round(r.cedisIn).toLocaleString("en-GB")} sent, grew to
              GH₵{Math.round(r.netOut).toLocaleString("en-GB")} after charges
            </p>

            <div
              className="mt-4 grid grid-cols-3 gap-3 border-t pt-3.5"
              style={{ borderColor: "rgba(255,255,255,0.25)" }}
            >
              <div>
                <p className="text-[10px] uppercase tracking-wider opacity-75">
                  The fund earned
                </p>
                <p className="mt-1 text-[1.05rem] font-bold tabular-nums leading-none sm:text-[1.25rem]">
                  +{money(r.fundGainHome)}
                </p>
                <p className="mt-1 text-[10.5px] opacity-70">
                  {r.fundOnlyPct.toFixed(2)}% a year, before charges
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider opacity-75">
                  The currency
                </p>
                <p
                  className="mt-1 text-[1.05rem] font-bold tabular-nums leading-none sm:text-[1.25rem]"
                  style={{
                    color: r.currencyEffect >= 0 ? "#8FE3BC" : "#FFC9BC",
                  }}
                >
                  {r.currencyEffect >= 0 ? "+" : "−"}
                  {money(r.currencyEffect)}
                </p>
                <p className="mt-1 text-[10.5px] opacity-70">
                  {r.currencyEffect >= 0
                    ? "the cedi moved in your favour"
                    : "the cedi moved against you"}
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider opacity-75">
                  Charges took
                </p>
                <p className="mt-1 text-[1.05rem] font-bold tabular-nums leading-none sm:text-[1.25rem]">
                  −{money(r.chargeCostHome)}
                </p>
                <p className="mt-1 text-[10.5px] opacity-70">
                  {fund.chargePct.toFixed(2)}% a year
                </p>
              </div>
            </div>
          </section>
        )}

        {/* Everything above is editable. */}
        <section
          className="mt-5 rounded-2xl p-5 sm:p-6"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2 className="text-[14px] font-bold">Change any of it</h2>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label="You send">
              <div className="flex gap-2">
                <select
                  value={ccy}
                  onChange={(e) => setCcy(e.target.value)}
                  className="cursor-pointer rounded-xl px-3 py-2.5 text-[14px]"
                  style={inputStyle}
                >
                  {CURRENCIES.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.code}
                    </option>
                  ))}
                </select>
                <input
                  inputMode="decimal"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full rounded-xl px-3 py-2.5 text-[14px] tabular-nums"
                  style={inputStyle}
                />
              </div>
            </Field>

            <Field label="Into">
              <select
                value={fundId}
                onChange={(e) => {
                  const f = OPTIONS.find((o) => o.id === e.target.value);
                  setFundId(e.target.value);
                  // Only overwrite the return if the visitor has not set their
                  // own — otherwise switching funds would silently discard it.
                  if (f && !touchedReturn) setReturnPct(String(f.returnPct));
                }}
                className="w-full cursor-pointer rounded-xl px-3 py-2.5 text-[14px]"
                style={inputStyle}
              >
                {OPTIONS.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
            </Field>

            <Field
              label="Cedis per 1 unit, when you send"
              hint="The rate you actually got, not the published one — your provider's margin is part of the cost."
            >
              <input
                inputMode="decimal"
                value={rateOut}
                onChange={(e) => setRateOut(e.target.value)}
                className="w-full rounded-xl px-3 py-2.5 text-[14px] tabular-nums"
                style={inputStyle}
              />
            </Field>

            <Field
              label="Cedis per 1 unit, when you take it out"
              hint="A lower number means the cedi strengthened, which works in your favour."
            >
              <input
                inputMode="decimal"
                value={rateBack}
                onChange={(e) => setRateBack(e.target.value)}
                className="w-full rounded-xl px-3 py-2.5 text-[14px] tabular-nums"
                style={inputStyle}
              />
            </Field>

            <Field label="Years invested">
              <input
                inputMode="decimal"
                value={years}
                onChange={(e) => setYears(e.target.value)}
                className="w-full rounded-xl px-3 py-2.5 text-[14px] tabular-nums"
                style={inputStyle}
              />
            </Field>

            <Field
              label="Annual return, %"
              hint={
                touchedReturn
                  ? "Your figure, not a published one."
                  : `${fund.name} published ${fund.returnPct}% over ${fund.window}. Change it to test your own assumption.`
              }
            >
              <input
                inputMode="decimal"
                value={returnPct}
                onChange={(e) => {
                  setReturnPct(e.target.value);
                  setTouchedReturn(true);
                }}
                className="w-full rounded-xl px-3 py-2.5 text-[14px] tabular-nums"
                style={inputStyle}
              />
            </Field>
          </div>

          <p className="mt-4 text-[12.5px]" style={{ color: C.muted }}>
            {fund.note}
          </p>
        </section>

        {/* The honest limits, not buried. */}
        <section
          className="mt-6 rounded-2xl p-5 sm:p-6"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2 className="text-[15px] font-bold">What this is not</h2>
          <ul
            className="mt-3 space-y-2.5 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            <li>
              <strong style={{ color: C.ink }}>Not a forecast.</strong> Every
              figure above is arithmetic on numbers you can see and change. The
              return is pre-filled with what a fund published over a stated
              period, which is what already happened rather than what will.
            </li>
            <li>
              <strong style={{ color: C.ink }}>Not advice.</strong> Telling you
              which product suits your circumstances is a personal
              recommendation and needs a licence from the Securities and
              Exchange Commission, which we do not have.
            </li>
            <li>
              <strong style={{ color: C.ink }}>Not the whole cost.</strong> The
              charge shown is the fund&rsquo;s. Your transfer provider takes a
              margin on the exchange rate, your bank may charge to receive, and
              withholding tax may apply. Enter the rate you actually got and
              the first of those is captured.
            </li>
            <li>
              <strong style={{ color: C.ink }}>
                Only five products, because only eight funds publish enough.
              </strong>{" "}
              Ghana has around 75. Most publish neither their charges nor their
              returns in a form anyone can check.
            </li>
          </ul>

          <p className="mt-5 text-[13.5px]">
            <Link
              href="/insights/sending-money-home-is-not-investing-it"
              className="font-semibold underline underline-offset-4"
              style={{ color: C.deep }}
            >
              Why the currency matters more than the fund →
            </Link>
          </p>
        </section>
      </div>

      <Footer />
    </main>
  );
}
