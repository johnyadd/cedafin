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

/*
  Cedis first, because most readers are in Ghana.

  Choosing GHS removes the exchange step entirely: someone investing cedis in
  a cedi fund has no currency effect to separate out, and asking them for a
  cedis-per-cedi rate would be nonsense. The rates are fixed at 1 and the row
  is hidden — the arithmetic is unchanged, so there is no special case to
  maintain.
*/
const CURRENCIES = [
  { code: "GHS", symbol: "GH₵", label: "Cedis — I'm in Ghana" },
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

/**
 * The three-way split, rendered in two places: inside the result card on a
 * desktop, and below the form on a phone. Same markup, so they cannot drift.
 */
interface Result {
  amt: number;
  cedisIn: number;
  grossOut: number;
  netOut: number;
  homeBack: number;
  totalGain: number;
  totalPct: number;
  fundGainHome: number;
  chargeCostHome: number;
  currencyEffect: number;
  fundOnlyPct: number;
}

function Split({
  r,
  money,
  fund,
  local,
}: {
  r: Result;
  money: (v: number) => string;
  fund: (typeof OPTIONS)[number];
  /** Cedi investor — no exchange step, so no currency column. */
  local: boolean;
}) {
  return (
    <>
      <div>
        <p className="text-[9.5px] uppercase tracking-wider opacity-75">
          The fund earned
        </p>
        <p className="mt-1 text-[1.05rem] font-bold tabular-nums leading-none">
          +{money(r.fundGainHome)}
        </p>
        <p className="mt-1 text-[10px] opacity-70">
          {r.fundOnlyPct.toFixed(2)}% a year, before charges
        </p>
      </div>
      {!local && (
      <div>
        <p className="text-[9.5px] uppercase tracking-wider opacity-75">
          The currency
        </p>
        <p
          className="mt-1 text-[1.05rem] font-bold tabular-nums leading-none"
          style={{ color: r.currencyEffect >= 0 ? "#8FE3BC" : "#FFC9BC" }}
        >
          {r.currencyEffect >= 0 ? "+" : "−"}
          {money(r.currencyEffect)}
        </p>
        <p className="mt-1 text-[10px] opacity-70">
          {r.currencyEffect >= 0 ? "moved in your favour" : "moved against you"}
        </p>
      </div>
      )}
      <div>
        <p className="text-[9.5px] uppercase tracking-wider opacity-75">
          Charges took
        </p>
        <p className="mt-1 text-[1.05rem] font-bold tabular-nums leading-none">
          −{money(r.chargeCostHome)}
        </p>
        <p className="mt-1 text-[10px] opacity-70">
          {fund.chargePct.toFixed(2)}% a year
        </p>
      </div>
    </>
  );
}

export default function CalculatorPage() {
  const [amount, setAmount] = useState("5000");
  const [ccy, setCcy] = useState("GHS");
  const [fundId, setFundId] = useState("faif");
  // Both 1 for cedis, so the exchange step is a no-op rather than a branch.
  const [rateOut, setRateOut] = useState("1");
  const [rateBack, setRateBack] = useState("1");
  const [years, setYears] = useState("1");
  const [returnPct, setReturnPct] = useState("34.73");
  const [touchedReturn, setTouchedReturn] = useState(false);

  const fund = OPTIONS.find((f) => f.id === fundId) ?? OPTIONS[0];
  const cur = CURRENCIES.find((c) => c.code === ccy) ?? CURRENCIES[0];
  const local = ccy === "GHS";

  const r = useMemo(() => {
    const amt = Number(amount) || 0;
    const out = Number(rateOut) || 0;
    const back = Number(rateBack) || 0;
    const yrs = Math.max(0.25, Number(years) || 1);
    const ret = (Number(returnPct) || 0) / 100;
    const chg = fund.chargePct / 100;

    // Returning null blanked the whole card the moment someone cleared a
    // field to type a new number. Better to show zeros and fill in as they go.
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
      // Zero over zero is NaN, which appeared on screen when the amount was
      // cleared.
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
          What a fund's charge actually costs you over time — and, if you are
          sending money from abroad, how much of your outcome was the exchange
          rate rather than the fund.
        </p>

        {/*
          The answer, before anything is asked — and it follows you down the
          page.

          The value of this tool is not seeing a result once. It is watching
          the number move when you change a rate, which you cannot do if the
          result has scrolled off the top by the time you reach the input.

          The header is already sticky at 0, so this sits below it.
        */}
        {/*
          Side by side on desktop, so the connection between the form and the
          result needs no explaining — you change a figure on the left and
          watch the number move on the right.

          On a phone they stack, and the order is the awkward part. Result
          first means an immediate answer but pushes the form below the fold;
          form first opens with an empty-looking page, which is what this
          design set out to avoid.

          So on mobile the result splits: a compact headline stays on top, and
          the three-way breakdown moves BELOW the form. Small enough that the
          first field is visible without scrolling, and the detail is still
          there for anyone who reads that far.
        */}
        <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)] lg:items-start">
          {/* Result — first on mobile, right-hand column on desktop. */}
          <div className="order-1 lg:order-2 lg:sticky lg:top-[76px]">
            {!r ? (
              <section
                className="rounded-2xl p-5 text-[14px]"
                style={{
                  background: C.card,
                  border: `1px solid ${C.gold}`,
                  color: C.muted,
                }}
              >
                <strong style={{ color: C.ink }}>
                  Enter your {ccy} exchange rates
                </strong>{" "}
                — the rate you got when you sent, and the rate now. Everything
                else is already filled in.
              </section>
            ) : (
              <section
                className="overflow-hidden rounded-2xl p-5 text-white sm:p-6"
                style={{
                  background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 72%)`,
                }}
              >
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] opacity-80">
                  {money(r.amt)} in {fund.name}, over {years}{" "}
                  {Number(years) === 1 ? "year" : "years"}
                </p>
                <p
                  className="mt-1.5 text-[2rem] font-bold tabular-nums leading-none sm:text-[2.5rem]"
                  style={{ color: r.totalGain >= 0 ? C.gold : "#FFC9BC" }}
                >
                  {money(r.homeBack)}
                </p>
                <p className="mt-1.5 text-[13px] opacity-90">
                  {r.totalGain >= 0 ? "Up" : "Down"} {money(r.totalGain)} —{" "}
                  {r.totalPct >= 0 ? "+" : ""}
                  {r.totalPct.toFixed(1)}% on what you sent
                </p>
                {!local && (
                  <p className="mt-0.5 text-[11px] opacity-70">
                    GH₵{Math.round(r.cedisIn).toLocaleString("en-GB")} sent,
                    grew to GH₵{Math.round(r.netOut).toLocaleString("en-GB")}{" "}
                    after charges
                  </p>
                )}

                {/*
                  The breakdown. Hidden here on a phone and repeated below the
                  form, so the headline stays short enough to keep the first
                  input in view.
                */}
                <div
                  className={`mt-4 hidden gap-4 border-t pt-4 lg:grid ${
                local ? "lg:grid-cols-2" : ""
              }`}
                  style={{ borderColor: "rgba(255,255,255,0.25)" }}
                >
                  <Split r={r} money={money} fund={fund} local={local} />
                </div>
              </section>
            )}
          </div>

          {/* Form — second on mobile, left-hand column on desktop. */}
          <section
            className="order-2 rounded-2xl p-5 sm:p-6 lg:order-1"
            style={{ background: C.card, border: `1px solid ${C.rule}` }}
          >
            <h2 className="text-[14px] font-bold">Change any of it</h2>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Field
                label="Currency and amount you send"
                hint={
                  !local && (rateOut === "" || rateBack === "")
                    ? `Now enter your ${ccy} rates below.`
                    : undefined
                }
              >
                <div className="flex gap-2">
                  <select
                    value={ccy}
                    onChange={(e) => {
                      /*
                        Clearing the rates rather than flagging them.

                        Someone switching GBP to USD keeps 15.20 and 14.50 —
                        pound rates silently applied to dollars, producing a
                        result that looks plausible and is wrong.

                        A warning would not fix it. Form research is consistent
                        that pre-filled values get skipped: people scan quickly
                        and do not re-read a field that already has something
                        in it. An empty box cannot be skipped.
                      */
                      const next = e.target.value;
                      setCcy(next);
                      // Cedis need no conversion, so 1 and 1. Anything else
                      // clears, because a pound rate silently applied to
                      // dollars produces a plausible wrong answer.
                      setRateOut(next === "GHS" ? "1" : "");
                      setRateBack(next === "GHS" ? "1" : "");
                    }}
                    className="cursor-pointer rounded-xl px-3 py-2.5 text-[14px]"
                    style={inputStyle}
                  >
                    {CURRENCIES.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.code} — {c.label}
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
                    // Only overwrite the return if the visitor has not set
                    // their own — otherwise switching funds discards it.
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

              {/* The currency is named in the label, so a stale figure would
                  be visible even if the clearing above ever failed. Hidden
                  entirely for cedis — there is nothing to convert. */}
              {!local && (
              <Field
                label={`Cedis per 1 ${ccy}, when you send`}
                hint="The rate you actually got, not the published one — your provider's margin is part of the cost."
              >
                <input
                  inputMode="decimal"
                  placeholder={`cedis per ${cur.symbol}1`}
                  value={rateOut}
                  onChange={(e) => setRateOut(e.target.value)}
                  className="w-full rounded-xl px-3 py-2.5 text-[14px] tabular-nums"
                  style={{
                    ...inputStyle,
                    borderColor: rateOut === "" ? C.gold : C.rule,
                  }}
                />
              </Field>
              )}

              {!local && (
              <Field
                label={`Cedis per 1 ${ccy}, when you take it out`}
                hint="A lower number means the cedi strengthened, which works in your favour."
              >
                <input
                  inputMode="decimal"
                  placeholder={`cedis per ${cur.symbol}1`}
                  value={rateBack}
                  onChange={(e) => setRateBack(e.target.value)}
                  className="w-full rounded-xl px-3 py-2.5 text-[14px] tabular-nums"
                  style={{
                    ...inputStyle,
                    borderColor: rateBack === "" ? C.gold : C.rule,
                  }}
                />
              </Field>
              )}

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
                    : `${fund.name} published ${fund.returnPct}% over ${fund.window}.`
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

          {/* The breakdown, on mobile only — below the form, where there is
              room for it. */}
          {r && (
            <section
              className={`order-3 grid gap-3 rounded-2xl p-5 text-white lg:hidden ${
                local ? "grid-cols-2" : "grid-cols-3"
              }`}
              style={{
                background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 72%)`,
              }}
            >
              <Split r={r} money={money} fund={fund} local={local} />
            </section>
          )}
        </div>

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
