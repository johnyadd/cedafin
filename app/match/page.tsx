"use client";

/**
 * app/match/page.tsx — eight questions, then what fits.
 *
 * WHY THIS IS A CLIENT COMPONENT WITH NO PERSISTENCE
 * Age band, what someone is saving for, how much they hold — that is personal
 * financial data under Ghana's Data Protection Act 2012. Storing it means a
 * lawful basis, a retention position, and a way for someone to get it deleted.
 * None of that is built. So the answers live in React state, go nowhere, and
 * vanish when the tab closes. The page says so, because a Ghanaian saver
 * typing their age into a site they have never heard of deserves to know.
 *
 * TWO OUTPUTS, ONE REGULATORY LINE
 *
 *   THE FILTER runs. It applies criteria the person stated to facts providers
 *   published. "You have GH¢50 and may need it within three months" excludes a
 *   fund with a GH¢1,000 minimum. That is arithmetic, not advice.
 *
 *   THE RECOMMENDER does not. Weighing someone's age against their horizon and
 *   concluding which product suits them is a personal recommendation, and
 *   giving one without an SEC licence would be exactly the thing this site
 *   tells providers off for — claiming more than you are entitled to.
 *
 * So the recommender is built and visibly withheld. A visitor sees the panel,
 * sees what it would say, and sees why it is switched off. That demonstrates
 * the whole concept without pretending to an authority we do not have.
 *
 * WHAT WE ASK BUT CANNOT USE
 * Four of the eight questions — age, purpose, regular contributions, existing
 * holdings — have nothing to filter against, because no Ghanaian provider
 * publishes anything they would match. They are asked because the recommender
 * needs them, and the results page says plainly which answers shaped the list
 * and which did not. A questionnaire that implies every answer mattered is a
 * small dishonesty, and this site does not get to make those.
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

interface Fund {
  id: string;
  slug: string;
  name: string;
  provider: string;
  assetClass: string;
  currency: string;
  chargesPct: number | null;
  minimumGhs: number | null;
  dealingFrequency: string | null;
  lockInDays: number | null;
  headlineReturn: { pct: number; window: string } | null;
}

type Answers = {
  ageBand?: string;
  amountGhs?: number;
  regular?: string;
  horizon?: string;
  purpose?: string;
  dropReaction?: string;
  assets: string[];
  hasExisting?: string;
  currency?: string;
};

const HORIZON_DAYS: Record<string, number> = {
  under3m: 90,
  "3to12m": 365,
  "1to3y": 1095,
  "3to5y": 1825,
  over5y: 3650,
};
const DEALING_DAYS: Record<string, number> = {
  daily: 1,
  weekly: 7,
  monthly: 30,
  quarterly: 90,
  at_maturity: 365,
  on_application: 30,
};
const ASSET_RISK: Record<string, number> = {
  government_security: 1,
  deposit: 1,
  money_market: 2,
  fixed_income: 3,
  balanced: 4,
  equity: 5,
  real_estate: 5,
};
const REACTION_CEILING: Record<string, number> = {
  sell: 2,
  worry: 3,
  hold: 4,
  buymore: 5,
};

const ASSET_LABEL: Record<string, string> = {
  money_market: "Money market",
  fixed_income: "Fixed income",
  balanced: "Balanced",
  equity: "Equity",
  real_estate: "Property",
  government_security: "Treasury bills",
};

const QUESTIONS = [
  {
    key: "ageBand",
    q: "How old are you?",
    why: "Used only for suitability guidance, which is switched off.",
    options: [
      ["under25", "Under 25"],
      ["25to34", "25 to 34"],
      ["35to49", "35 to 49"],
      ["50to64", "50 to 64"],
      ["65plus", "65 or over"],
    ],
  },
  {
    key: "amount",
    q: "How much are you starting with?",
    why: "Filters out funds whose minimum is above this.",
    options: [
      ["50", "Under GH₵100"],
      ["500", "GH₵100 to 1,000"],
      ["5000", "GH₵1,000 to 10,000"],
      ["50000", "GH₵10,000 to 100,000"],
      ["200000", "Over GH₵100,000"],
    ],
  },
  {
    key: "regular",
    q: "Will you add to it regularly?",
    why: "For suitability guidance only.",
    options: [
      ["yes", "Yes, monthly or so"],
      ["sometimes", "When I can"],
      ["no", "No, this is a one-off"],
    ],
  },
  {
    key: "horizon",
    q: "When might you need this money back?",
    why: "Filters out funds that lock money longer than this.",
    options: [
      ["under3m", "Within 3 months"],
      ["3to12m", "3 to 12 months"],
      ["1to3y", "1 to 3 years"],
      ["3to5y", "3 to 5 years"],
      ["over5y", "More than 5 years"],
    ],
  },
  {
    key: "purpose",
    q: "What is it for?",
    why: "For suitability guidance only.",
    options: [
      ["emergency", "Emergency fund"],
      ["house", "A house or land"],
      ["school", "School fees"],
      ["retirement", "Retirement"],
      ["growth", "Growing it generally"],
      ["other", "Something else"],
    ],
  },
  {
    key: "dropReaction",
    q: "If this fell 20% in a month, what would you do?",
    why: "Flags where your answers pull in different directions.",
    options: [
      ["sell", "Take my money out"],
      ["worry", "Worry, but leave it"],
      ["hold", "Leave it and not think much about it"],
      ["buymore", "Put more in while it's cheap"],
    ],
  },
  {
    key: "assets",
    q: "Which kinds of investment interest you?",
    why: "Filters the list to these. Choose as many as you like.",
    multi: true,
    options: [
      ["money_market", "Money market — steady, low risk"],
      ["fixed_income", "Fixed income — bonds and bills"],
      ["balanced", "Balanced — a mix"],
      ["equity", "Equity — shares, higher risk"],
      ["government_security", "Treasury bills — government, no charges"],
      ["real_estate", "Property"],
    ],
  },
  {
    key: "hasExisting",
    q: "Do you already have savings or investments?",
    why: "For suitability guidance only.",
    options: [
      ["none", "No, this is my first"],
      ["savings", "Savings account only"],
      ["some", "Some investments already"],
    ],
  },
] as const;


/**
 * WHAT THIS WOULD HAVE DONE — never what it will do.
 *
 * Every return on this site was measured over a stated window, in a rate
 * environment that no longer exists. Stanbic Income Fund returned 38.80% in a
 * year when Treasury bills paid around 25%. Bills now pay about 5%. Running
 * that 38.80% forward would produce a number no fund in Ghana will deliver,
 * and somebody might plan around it.
 *
 * So the projection is arithmetic on a measured past, in the past tense, and
 * the period control stops at the window actually measured. Beyond that point
 * there is no observation to compound — only a guess with a slider attached.
 */
function projectionCap(windowLabel: string | null): number {
  if (!windowLabel) return 1;
  const m = /^(\d+)\s*([ymd])/i.exec(windowLabel.trim());
  if (!m) return 1;
  const n = Number(m[1]);
  const unit = m[2].toLowerCase();
  const years = unit === "y" ? n : unit === "m" ? n / 12 : n / 365;
  return Math.max(1, Math.round(years));
}

function grow(amount: number, annualPct: number, years: number): number {
  return amount * Math.pow(1 + annualPct / 100, years);
}

const AMOUNT_PRESETS = [100, 1000, 5000, 20000, 100000];

export default function MatchPage() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Answers>({ assets: [] });
  const [funds, setFunds] = useState<Fund[] | null>(null);
  /**
   * Live controls on the results page. Changing the amount re-runs the whole
   * filter — funds excluded on their minimum reappear when you raise it, which
   * is the single most useful thing someone can discover here.
   */
  const [tryAmount, setTryAmount] = useState<number | null>(null);
  /**
   * Years to project. Capped per fund at its ACTUAL measured window: see
   * `projectionCap`. Dragging past what was measured stops being arithmetic
   * and starts being a forecast, which is a different claim entirely.
   */
  const [tryYears, setTryYears] = useState<number>(1);
  /**
   * Horizon and asset types are live for the same reason amount is: they are
   * things the filter ACTS ON, so changing one changes the shortlist. Someone
   * exploring "what if I could leave it three years instead of three months"
   * should not have to answer eight questions again to find out.
   *
   * Four answers are deliberately NOT adjustable here — age, what it's for,
   * regular contributions, existing holdings. Nothing any Ghanaian provider
   * publishes can be matched against them, so a control would imply an effect
   * it does not have. A dial that moves nothing is worse than no dial.
   *
   * The 20%-fall question is also fixed, and for a different reason: it drives
   * the contradiction warning. Letting someone toggle it until the warning
   * disappears would defeat the point of raising it.
   */
  const [tryHorizon, setTryHorizon] = useState<string | null>(null);
  const [tryAssets, setTryAssets] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const done = step >= QUESTIONS.length;

  async function loadFunds() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/funds");
      if (!res.ok) throw new Error(`funds request failed (${res.status})`);
      setFunds(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "could not load funds");
    } finally {
      setLoading(false);
    }
  }

  function answer(key: string, value: string, multi?: boolean) {
    if (multi) {
      setAnswers((a) => ({
        ...a,
        assets: a.assets.includes(value)
          ? a.assets.filter((v) => v !== value)
          : [...a.assets, value],
      }));
      return;
    }
    setAnswers((a) => ({
      ...a,
      ...(key === "amount" ? { amountGhs: Number(value) } : { [key]: value }),
    }));
    advance();
  }

  function advance() {
    setStep((s) => {
      const next = s + 1;
      if (next >= QUESTIONS.length && !funds) void loadFunds();
      return next;
    });
  }

  const outcome = useMemo(() => {
    if (!funds) return null;
    const matches: { f: Fund; meets: string[]; unchecked: string[] }[] = [];
    const excluded: { f: Fund; because: string }[] = [];
    const conflicts: string[] = [];

    const liveAssets = tryAssets ?? answers.assets;
    const liveHorizon = tryHorizon ?? answers.horizon;
    if (answers.dropReaction && liveAssets.length) {
      const ceiling = REACTION_CEILING[answers.dropReaction] ?? 5;
      const risky = liveAssets.filter((c) => (ASSET_RISK[c] ?? 3) > ceiling);
      if (risky.length) {
        conflicts.push(
          `You said you'd ${
            answers.dropReaction === "sell" ? "take your money out" : "worry"
          } if this fell 20%, but asked to see ${risky
            .map((r) => (ASSET_LABEL[r] ?? r).toLowerCase())
            .join(" and ")} funds — where falls like that are normal. Both are below; they pull in different directions.`,
        );
      }
    }
    if (liveHorizon === "under3m" && liveAssets.includes("equity")) {
      conflicts.push(
        "Equity funds are held for years, not months. Over three months, what the market does matters more than what the fund does.",
      );
    }

    const activeAssets = tryAssets ?? answers.assets;
    const activeHorizon = tryHorizon ?? answers.horizon;

    for (const f of funds) {
      const meets: string[] = [];
      const unchecked: string[] = [];

      if (activeAssets.length && !activeAssets.includes(f.assetClass)) {
        excluded.push({
          f,
          because: `${(ASSET_LABEL[f.assetClass] ?? f.assetClass).toLowerCase()}, not among the types you chose`,
        });
        continue;
      }
      if (activeAssets.length) meets.push("the kind of fund you asked for");

      const effectiveAmount = tryAmount ?? answers.amountGhs;
      if (effectiveAmount !== undefined) {
        if (f.minimumGhs === null) {
          unchecked.push("minimum — this provider doesn't publish one");
        } else if (f.minimumGhs > effectiveAmount) {
          excluded.push({
            f,
            because: `needs ${GHS.format(f.minimumGhs)} to start`,
          });
          continue;
        } else {
          meets.push(`takes ${GHS.format(effectiveAmount)} to start`);
        }
      }

      if (activeHorizon) {
        const want = HORIZON_DAYS[activeHorizon] ?? 365;
        if ((f.lockInDays ?? 0) > want) {
          excluded.push({
            f,
            because: `holds your money ${f.lockInDays} days — longer than you said`,
          });
          continue;
        }
        const d = f.dealingFrequency ? DEALING_DAYS[f.dealingFrequency] : null;
        if (d === null || d === undefined) {
          unchecked.push("how quickly you can withdraw — not published");
        } else if (d <= 1) {
          meets.push("money out any working day");
        } else if (d <= want) {
          meets.push(`money back within about ${d} days`);
        }
      }

      matches.push({ f, meets, unchecked });
    }

    matches.sort(
      (a, b) =>
        (a.f.chargesPct ?? 99) - (b.f.chargesPct ?? 99) ||
        a.f.name.localeCompare(b.f.name),
    );

    const unused: string[] = [];
    if (answers.ageBand) unused.push("your age");
    if (answers.purpose) unused.push("what it's for");
    if (answers.regular) unused.push("whether you'll add to it");
    if (answers.hasExisting) unused.push("what you already hold");

    return { matches, excluded, conflicts, unused };
  }, [funds, answers, tryAmount, tryHorizon, tryAssets]);

  const q = QUESTIONS[step];

  return (
    <main
      className="min-h-screen"
      style={{ background: C.bg, color: C.ink }}
    >
      <div
        className="w-full px-5 py-2 text-center text-[11px] font-medium tracking-wide text-white"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        Your answers stay in this browser · nothing is saved or sent
      </div>

      <header className="mx-auto max-w-2xl px-5 pt-6">
        <Link
          href="/"
          className="text-[19px] font-bold tracking-tight"
          style={{ color: C.deep }}
        >
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
                  style={{ background: i <= step ? C.teal : C.rule }}
                />
              ))}
            </div>
            <p className="mt-4 text-[11px] uppercase tracking-wider" style={{ color: C.muted }}>
              Question {step + 1} of {QUESTIONS.length}
            </p>

            <h1 className="mt-2 text-[1.7rem] font-bold leading-tight sm:text-[2.1rem]">
              {q.q}
            </h1>
            <p className="mt-2 text-[12.5px]" style={{ color: C.muted }}>
              {q.why}
            </p>

            <div className="mt-6 space-y-2.5">
              {q.options.map(([value, label]) => {
                const chosen =
                  "multi" in q && q.multi
                    ? answers.assets.includes(value)
                    : (answers as Record<string, unknown>)[
                        q.key === "amount" ? "amountGhs" : q.key
                      ] === (q.key === "amount" ? Number(value) : value);
                return (
                  <button
                    key={value}
                    onClick={() => answer(q.key, value, "multi" in q && q.multi)}
                    className="w-full rounded-2xl px-5 py-4 text-left text-[14.5px] font-medium transition-colors"
                    style={{
                      background: chosen ? `${C.teal}14` : C.card,
                      border: `1px solid ${chosen ? C.teal : C.rule}`,
                      color: C.ink,
                    }}
                  >
                    {label}
                  </button>
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
                style={{ background: C.deep }}
              >
                {"multi" in q && q.multi ? "Show me what fits →" : "Skip →"}
              </button>
            </div>
          </>
        )}

        {done && (
          <>
            <h1 className="text-[1.9rem] font-bold leading-tight sm:text-[2.4rem]">
              What fits what you told us
            </h1>

            {loading && (
              <p className="mt-6 text-[14px]" style={{ color: C.muted }}>
                Checking the funds…
              </p>
            )}
            {error && (
              <p className="mt-6 text-[14px]" style={{ color: C.clay }}>
                {error}
              </p>
            )}

            {outcome && (
              <>
                {outcome.conflicts.map((c) => (
                  <p
                    key={c}
                    className="mt-5 rounded-2xl px-5 py-4 text-[13.5px] leading-relaxed"
                    style={{ background: `${C.gold}1A` }}
                  >
                    <strong>Worth knowing.</strong> {c}
                  </p>
                ))}

                {/* Live controls. Changing the amount re-runs the filter, so
                    funds excluded on their minimum reappear as you raise it —
                    which is the most useful thing to discover on this page. */}
                <section
                  className="mt-6 rounded-2xl p-5"
                  style={{ background: C.card, border: `1px solid ${C.rule}` }}
                >
                  <p className="text-[12px] font-semibold uppercase tracking-wider"
                     style={{ color: C.muted }}>
                    Change your answers, see what changes
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
                            background: on ? C.deep : C.bg,
                            color: on ? "#fff" : C.ink,
                            border: `1px solid ${on ? C.deep : C.rule}`,
                          }}
                        >
                          {GHS.format(v)}
                        </button>
                      );
                    })}
                    {tryAmount !== null &&
                      tryAmount !== answers.amountGhs && (
                        <button
                          onClick={() => {
                            setTryAmount(null);
                            setTryHorizon(null);
                            setTryAssets(null);
                          }}
                          className="rounded-full px-4 py-2 text-[13px]"
                          style={{ color: C.muted }}
                        >
                          reset all
                        </button>
                      )}
                  </div>

                  <p className="mt-5 text-[12px] font-semibold uppercase tracking-wider"
                     style={{ color: C.muted }}>
                    When you might need it back
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {[
                      ["under3m", "3 months"],
                      ["3to12m", "1 year"],
                      ["1to3y", "1–3 years"],
                      ["3to5y", "3–5 years"],
                      ["over5y", "5+ years"],
                    ].map(([v, label]) => {
                      const on = (tryHorizon ?? answers.horizon) === v;
                      return (
                        <button
                          key={v}
                          onClick={() => setTryHorizon(v)}
                          className="rounded-full px-4 py-2 text-[13px] font-semibold"
                          style={{
                            background: on ? C.deep : C.bg,
                            color: on ? "#fff" : C.ink,
                            border: `1px solid ${on ? C.deep : C.rule}`,
                          }}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>

                  <p className="mt-5 text-[12px] font-semibold uppercase tracking-wider"
                     style={{ color: C.muted }}>
                    Kinds of fund
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {Object.entries(ASSET_LABEL).map(([v, label]) => {
                      const active = tryAssets ?? answers.assets;
                      const on = active.includes(v);
                      return (
                        <button
                          key={v}
                          onClick={() =>
                            setTryAssets(
                              on
                                ? active.filter((x) => x !== v)
                                : [...active, v],
                            )
                          }
                          className="rounded-full px-4 py-2 text-[13px] font-semibold"
                          style={{
                            background: on ? `${C.teal}1A` : C.bg,
                            color: on ? C.deep : C.muted,
                            border: `1px solid ${on ? C.teal : C.rule}`,
                          }}
                        >
                          {on ? "✓ " : ""}
                          {label}
                        </button>
                      );
                    })}
                  </div>

                  <div className="mt-5 flex flex-wrap items-center gap-3">
                    <span className="text-[12px] font-semibold uppercase tracking-wider"
                          style={{ color: C.muted }}>
                      Over
                    </span>
                    {[1, 2, 3, 5].map((y) => {
                      const on = tryYears === y;
                      return (
                        <button
                          key={y}
                          onClick={() => setTryYears(y)}
                          className="rounded-full px-3.5 py-1.5 text-[12.5px] font-semibold"
                          style={{
                            background: on ? `${C.teal}1A` : "transparent",
                            color: on ? C.deep : C.muted,
                            border: `1px solid ${on ? C.teal : C.rule}`,
                          }}
                        >
                          {y} year{y > 1 ? "s" : ""}
                        </button>
                      );
                    })}
                  </div>
                  <p className="mt-3 text-[11.5px] leading-relaxed"
                     style={{ color: C.muted }}>
                    Periods longer than a fund actually measured are marked, not
                    shown — there is nothing observed to compound beyond that
                    point. Your age, what you&rsquo;re saving for and what you
                    already hold aren&rsquo;t adjustable here, because no
                    provider publishes anything to match them against —
                    changing them would move nothing.
                  </p>
                </section>

                <p className="mt-5 text-[14px]" style={{ color: C.muted }}>
                  {outcome.matches.length} of {funds?.length ?? 0} funds match
                  what you said. Cheapest first — cost is the one thing every
                  provider discloses.
                </p>

                <ol className="mt-6 space-y-3">
                  {outcome.matches.map((m, i) => (
                    <li
                      key={m.f.id}
                      className="rounded-2xl p-5"
                      style={{
                        background: C.card,
                        border: `1px solid ${i === 0 ? C.gold : C.rule}`,
                      }}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <h2 className="text-[15.5px] font-bold">{m.f.name}</h2>
                          <p className="mt-0.5 text-[12px]" style={{ color: C.muted }}>
                            {m.f.provider}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[1.4rem] font-bold tabular-nums leading-none">
                            {m.f.chargesPct !== null
                              ? `${m.f.chargesPct.toFixed(2)}%`
                              : "—"}
                          </p>
                          <p className="text-[10.5px]" style={{ color: C.muted }}>
                            a year in charges
                          </p>
                        </div>
                      </div>

                      {m.meets.length > 0 && (
                        <ul className="mt-3 space-y-1">
                          {m.meets.map((x) => (
                            <li
                              key={x}
                              className="text-[12.5px]"
                              style={{ color: C.good }}
                            >
                              ✓ {x}
                            </li>
                          ))}
                        </ul>
                      )}
                      {/* Charges made concrete. This is the site's whole
                          argument: 2.25% against 1.75% is abstract, GH¢1,125
                          against GH¢875 a year is not. Shown for every fund,
                          because every fund publishes a charge. */}
                      {(() => {
                        const amt = tryAmount ?? answers.amountGhs;
                        if (!amt || m.f.chargesPct === null) return null;
                        const annualCost = (amt * m.f.chargesPct) / 100;
                        const cap = projectionCap(m.f.headlineReturn?.window ?? null);
                        const years = Math.min(tryYears, cap);
                        const capped = tryYears > cap;
                        const ret = m.f.headlineReturn;
                        return (
                          <div
                            className="mt-4 rounded-xl px-4 py-3"
                            style={{ background: C.bg }}
                          >
                            <p className="text-[12.5px]">
                              <strong>{GHS.format(amt)}</strong> costs{" "}
                              <strong style={{ color: C.clay }}>
                                {GHS.format(annualCost)}
                              </strong>{" "}
                              a year in charges
                              {years > 1 && (
                                <> — {GHS.format(annualCost * years)} over {years} years</>
                              )}
                              .
                            </p>

                            {ret ? (
                              <p className="mt-1.5 text-[12.5px]" style={{ color: C.muted }}>
                                It returned{" "}
                                <strong style={{ color: C.ink }}>
                                  {ret.pct.toFixed(2)}%
                                </strong>{" "}
                                over {ret.window}. At that rate{" "}
                                {GHS.format(amt)} <em>would have become</em>{" "}
                                <strong style={{ color: C.ink }}>
                                  {GHS.format(grow(amt, ret.pct, years))}
                                </strong>{" "}
                                in {years} year{years > 1 ? "s" : ""}
                                {capped && (
                                  <>
                                    {" "}
                                    — capped at the {cap}-year window actually
                                    measured
                                  </>
                                )}
                                .
                              </p>
                            ) : (
                              <p className="mt-1.5 text-[12px]" style={{ color: C.muted }}>
                                No published return we can verify, so no figure
                                is shown.
                              </p>
                            )}
                          </div>
                        );
                      })()}

                      {m.unchecked.length > 0 && (
                        <ul className="mt-2 space-y-1">
                          {m.unchecked.map((x) => (
                            <li
                              key={x}
                              className="text-[12px]"
                              style={{ color: C.muted }}
                            >
                              ? {x}
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ol>

                {outcome.matches.length === 0 && (
                  <p
                    className="mt-5 rounded-2xl px-5 py-5 text-[13.5px] leading-relaxed"
                    style={{ background: C.card, border: `1px solid ${C.rule}` }}
                  >
                    Nothing we hold matches all of that. That may mean no such
                    fund exists in Ghana, or that we haven&rsquo;t got the
                    figures yet — 67 funds are listed with nothing against them.
                    Loosening one answer usually helps.
                  </p>
                )}

                {/* Said once, under the list, because it applies to every
                    figure above and repeating it per card would train people
                    to skip it. */}
                <p
                  className="mt-6 rounded-2xl px-5 py-4 text-[12.5px] leading-relaxed"
                  style={{ background: `${C.gold}1A` }}
                >
                  <strong>These are past figures, not forecasts.</strong> Every
                  return above was earned when Ghanaian Treasury bills paid
                  between 13% and 25%. They now pay around 5%. The same fund,
                  run the same way, would return far less today — so read these
                  as what happened, not what will.
                </p>

                {/* The recommender: built, visibly withheld. */}
                <section
                  className="mt-10 rounded-3xl p-6"
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
                      Which of these suits you
                    </h2>
                  </div>
                  <p
                    className="mt-3 text-[13.5px] leading-relaxed"
                    style={{ color: C.muted }}
                  >
                    We could weigh your age against your timeframe, check your
                    answers against each other and tell you which fund fits
                    best. That is a personal recommendation, and in Ghana it
                    needs a licence from the Securities and Exchange Commission.
                    We don&rsquo;t have one yet, so it stays off — the list
                    above filters on what you told us and nothing more.
                  </p>
                  <p className="mt-3 text-[12.5px]" style={{ color: C.muted }}>
                    A site that tells providers to publish what they can prove
                    doesn&rsquo;t get to claim authority it hasn&rsquo;t earned.
                  </p>
                </section>

                {outcome.unused.length > 0 && (
                  <p className="mt-6 text-[12.5px]" style={{ color: C.muted }}>
                    <strong>What didn&rsquo;t shape this list:</strong>{" "}
                    {outcome.unused.join(", ")}. No Ghanaian provider publishes
                    anything those could be matched against, so they were
                    collected for the guidance above rather than used to filter.
                  </p>
                )}

                {outcome.excluded.length > 0 && (
                  <details className="mt-4">
                    <summary
                      className="cursor-pointer text-[13px] font-semibold"
                      style={{ color: C.deep }}
                    >
                      {outcome.excluded.length} funds left out, and why
                    </summary>
                    <ul className="mt-3 space-y-1.5">
                      {outcome.excluded.map((e) => (
                        <li
                          key={e.f.id}
                          className="text-[12.5px]"
                          style={{ color: C.muted }}
                        >
                          <strong style={{ color: C.ink }}>{e.f.name}</strong> —{" "}
                          {e.because}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}

                <div className="mt-8 flex flex-wrap gap-3">
                  <button
                    onClick={() => {
                      setAnswers({ assets: [] });
                      setStep(0);
                    }}
                    className="rounded-full px-5 py-2.5 text-[13.5px] font-bold text-white"
                    style={{ background: C.deep }}
                  >
                    Start again
                  </button>
                  <Link
                    href="/funds"
                    className="rounded-full px-5 py-2.5 text-[13.5px] font-semibold"
                    style={{
                      background: C.card,
                      border: `1px solid ${C.rule}`,
                      color: C.ink,
                    }}
                  >
                    See every fund instead
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
