/**
 * lib/scoring/config.ts
 *
 * THE METHODOLOGY. Single source of truth.
 *
 * The Python engine receives this object in the /compute/scores payload, and
 * the public /methodology page renders FROM THIS FILE. Never describe the
 * weights anywhere else in prose — the moment the published methodology and the
 * executed methodology are two artifacts, they drift, and the drift is
 * invisible until a provider catches it.
 *
 * Changing any weight, factor, or gate = bump METHODOLOGY_VERSION and add a
 * CHANGELOG entry. Old score_runs are never recomputed or deleted.
 */

export const METHODOLOGY_VERSION = "1.0.0";

/** File revision. Distinct from METHODOLOGY_VERSION, which only moves when the
 *  scoring maths changes. v1.1 added DISPLAY_RULES, v1.2 added the deposit
 *  peer groups and net-of-tax display; the maths is unchanged. */
export const CONFIG_FILE_VERSION = "1.2";

export const CHANGELOG: Array<{ version: string; date: string; change: string }> = [
  { version: "1.0.0", date: "2026-08-20", change: "Initial published methodology." },
];

// ---------------------------------------------------------------------------
// Peer groups — the ONLY ranking universe.
// A money-market fund and an equity fund never share a leaderboard. There is
// deliberately no site-wide "#1 investment in Ghana".
// ---------------------------------------------------------------------------

export const PEER_GROUP_LABELS: Record<string, string> = {
  "money_market:GHS": "Cedi money market funds",
  "fixed_income:GHS": "Cedi fixed income funds",
  "balanced:GHS": "Cedi balanced funds",
  "equity:GHS": "Cedi equity funds",
  "government_security:GHS": "Government securities",
  "money_market:USD": "Dollar money market funds",
  "fixed_income:USD": "Dollar fixed income funds",
  // v1.2 — deposit products. A saver with GH₵1,000 is really choosing between
  // a money market fund, a fixed deposit, a T-bill and a savings account, so
  // excluding banks answers a narrower question than the one being asked.
  // They stay in their OWN peer group: a capital-guaranteed deposit and a
  // variable-NAV fund are not comparable on volatility or drawdown.
  "deposit:GHS": "Cedi fixed deposits and savings accounts",
  "deposit:USD": "Dollar fixed deposits and savings accounts",
};

export const MIN_PEER_GROUP_SIZE = 3; // below this, show factual comparison, no ranks

// ---------------------------------------------------------------------------
// Factors
//
// Note on 1.0.0: the return side is ONE factor, not two. Separating
// "risk-adjusted performance" from "historical performance" double-counts —
// the two are ~90% correlated and the pair silently makes return 35% of the
// score. One risk-adjusted factor at 20% is the honest weight.
// ---------------------------------------------------------------------------

export type FactorKey =
  | "risk_adjusted_return"
  | "cost"
  | "volatility"
  | "drawdown"
  | "consistency"
  | "liquidity"
  | "accessibility"
  | "provider_strength"
  | "transparency";

export interface Factor {
  key: FactorKey;
  label: string;
  /** Rendered verbatim on /methodology. Write it for an investor, not an engineer. */
  description: string;
  direction: "higher_better" | "lower_better";
  /** Columns that must be present and non-null, else the factor is unavailable. */
  requires: string[];
  /** Percentile-normalised within peer group (true) or on a fixed absolute scale (false). */
  peerRelative: boolean;
  /** Percentile clamp before normalisation, to stop one outlier compressing the field. */
  winsorise: [number, number];
}

export const FACTORS: Record<FactorKey, Factor> = {
  risk_adjusted_return: {
    key: "risk_adjusted_return",
    label: "Risk-adjusted return",
    description:
      "Return over the 91-day Treasury bill, divided by the fund's volatility, over the longest window with at least 12 months of verified prices. Rewards return that was not simply bought with extra risk.",
    direction: "higher_better",
    requires: ["excess_over_tbill", "volatility"],
    peerRelative: true,
    winsorise: [0.02, 0.98],
  },
  cost: {
    key: "cost",
    label: "Total cost",
    description:
      "Total expense ratio where published, otherwise the management fee plus any disclosed recurring charges. Exit and early-redemption charges are shown on the product page but are not scored here.",
    direction: "lower_better",
    requires: ["total_cost_rate"],
    peerRelative: true,
    winsorise: [0.02, 0.98],
  },
  volatility: {
    key: "volatility",
    label: "Volatility",
    description:
      "Annualised standard deviation of returns over the scoring window. Lower means a smoother ride, not a better fund.",
    direction: "lower_better",
    requires: ["volatility"],
    peerRelative: true,
    winsorise: [0.02, 0.98],
  },
  drawdown: {
    key: "drawdown",
    label: "Worst fall",
    description:
      "The largest peak-to-trough fall in unit price over the scoring window — the worst loss an investor would have lived through.",
    direction: "lower_better",
    requires: ["max_drawdown"],
    peerRelative: true,
    winsorise: [0.02, 0.98],
  },
  consistency: {
    key: "consistency",
    label: "Consistency",
    description:
      "The share of rolling monthly periods in which the fund returned more than inflation.",
    direction: "higher_better",
    requires: ["positive_period_pct"],
    peerRelative: true,
    winsorise: [0.05, 0.95],
  },
  liquidity: {
    key: "liquidity",
    label: "Access to your money",
    description:
      "How often the fund deals, how many business days redemption takes, and any lock-in period or early-exit penalty.",
    direction: "higher_better",
    requires: ["dealing_frequency", "redemption_days"],
    peerRelative: false,
    winsorise: [0, 1],
  },
  accessibility: {
    key: "accessibility",
    label: "Minimum investment",
    description:
      "The smallest amount that opens an account, plus whether it can be funded by mobile money.",
    direction: "lower_better",
    requires: ["min_initial_minor"],
    peerRelative: true,
    winsorise: [0.02, 0.98],
  },
  provider_strength: {
    key: "provider_strength",
    label: "Provider standing",
    description:
      "The provider's TrustScore: verified SEC licence, named custodian and trustee, published accounts and scheme particulars, and operating history.",
    direction: "higher_better",
    requires: ["trust_score"],
    peerRelative: false,
    winsorise: [0, 1],
  },
  transparency: {
    key: "transparency",
    label: "Transparency",
    description:
      "How completely and how recently the provider publishes prices, holdings and costs. A fund that does not publish cannot be assessed, and that is itself information.",
    direction: "higher_better",
    requires: ["disclosure_completeness", "data_freshness_days"],
    peerRelative: false,
    winsorise: [0, 1],
  },
};

// ---------------------------------------------------------------------------
// Profile weights. Each column must sum to 1.0 — asserted at module load.
// ---------------------------------------------------------------------------

export type InvestorProfile = "conservative" | "balanced" | "growth" | "beginner";

export const WEIGHTS: Record<InvestorProfile, Record<FactorKey, number>> = {
  conservative: {
    risk_adjusted_return: 0.15,
    cost:                 0.15,
    volatility:           0.15,
    drawdown:             0.15,
    consistency:          0.10,
    liquidity:            0.10,
    accessibility:        0.05,
    provider_strength:    0.10,
    transparency:         0.05,
  },
  balanced: {
    risk_adjusted_return: 0.20,
    cost:                 0.15,
    volatility:           0.10,
    drawdown:             0.10,
    consistency:          0.10,
    liquidity:            0.10,
    accessibility:        0.05,
    provider_strength:    0.15,
    transparency:         0.05,
  },
  growth: {
    risk_adjusted_return: 0.30,
    cost:                 0.15,
    volatility:           0.05,
    drawdown:             0.05,
    consistency:          0.15,
    liquidity:            0.05,
    accessibility:        0.05,
    provider_strength:    0.15,
    transparency:         0.05,
  },
  // Beginner deliberately underweights return. Someone investing for the first
  // time is best served by a cheap, liquid, low-minimum product from a
  // well-documented provider — not by last year's top performer.
  beginner: {
    risk_adjusted_return: 0.10,
    cost:                 0.20,
    volatility:           0.10,
    drawdown:             0.05,
    consistency:          0.05,
    liquidity:            0.15,
    accessibility:        0.15,
    provider_strength:    0.15,
    transparency:         0.05,
  },
};

// ---------------------------------------------------------------------------
// Gates. These are what stop the score being false precision.
// ---------------------------------------------------------------------------

export const GATES = {
  /** Below this weighted coverage the product is listed but NOT scored. */
  COVERAGE_FLOOR: 0.70,
  /** No score without this much verified price history. */
  MIN_HISTORY_MONTHS: 12,
  /** Minimum observations in the window before metrics are trusted. */
  MIN_OBSERVATIONS: 24,
  /** Beyond this, the product goes 'stale' and its score is suppressed. */
  MAX_DATA_AGE_DAYS: 14,
} as const;

export const UNSCORED_REASONS = {
  insufficient_coverage: "Not scored — not enough verified data published",
  insufficient_history: "New — less than 12 months of verified prices",
  stale_data: "Not scored — prices not published recently enough",
  small_peer_group: "Not ranked — too few comparable funds",
} as const;

// ---------------------------------------------------------------------------
// TrustScore. Built ONLY from facts that trace to a stored document.
//
// Deliberately omitted at 1.0.0: customer service (10) and complaint record
// (10). There is no data source for either, and inventing them would corrupt
// the one number whose entire value is that it is not invented. Add them when
// a survey or a regulator complaints register actually supplies them — as a
// version bump, with the change published.
// ---------------------------------------------------------------------------

export const TRUST_COMPONENTS = [
  { key: "licence_verified",    points: 30, label: "SEC licence verified and current" },
  { key: "custodian_named",     points: 15, label: "Custodian and trustee identified" },
  { key: "audited_accounts",    points: 15, label: "Audited financial statements available" },
  { key: "scheme_particulars",  points: 15, label: "Prospectus or scheme particulars published" },
  { key: "operating_history",   points: 10, label: "Years operating" },
  { key: "data_freshness",      points: 10, label: "Prices published on schedule" },
  { key: "disclosure_complete", points:  5, label: "Completeness of published product data" },
] as const;

// ---------------------------------------------------------------------------
// Benchmarks required for the engine to run at all.
// ---------------------------------------------------------------------------

/**
 * Tax handling (v1.2). Withholding on investment income differs by product
 * type and moves with the Finance Act, so rates live on the product row
 * (products.withholding_rate) with a source and a verified date — NEVER
 * hardcoded here. This block only defines how the bridge is presented.
 *
 * Confirm current Ghanaian treatment with an accountant before publishing.
 */
export const YIELD_BRIDGE_STEPS = [
  { key: "gross_yield",     label: "Gross yield" },
  { key: "less_fees",       label: "Less fees" },
  { key: "net_of_fees",     label: "Net of fees" },
  { key: "less_tax",        label: "Less withholding tax" },
  { key: "net_of_tax",      label: "What you receive" },
  { key: "less_inflation",  label: "Less inflation" },
  { key: "real_after_tax",  label: "What you actually keep" },
] as const;

export const REQUIRED_SERIES = {
  RISK_FREE: "GH_TBILL_91",
  INFLATION: "GH_CPI_YOY",
  EQUITY_BENCHMARK: "GSE_CI",
  FX: "GHS_USD",
} as const;

// ---------------------------------------------------------------------------
// Load-time assertions. A silently unnormalised weight column would produce
// scores that look plausible and are wrong.
// ---------------------------------------------------------------------------

for (const [profile, weights] of Object.entries(WEIGHTS)) {
  const sum = Object.values(weights).reduce((a, b) => a + b, 0);
  if (Math.abs(sum - 1) > 1e-9) {
    throw new Error(`Weights for profile "${profile}" sum to ${sum}, expected 1.0`);
  }
  for (const key of Object.keys(weights)) {
    if (!(key in FACTORS)) throw new Error(`Unknown factor "${key}" in profile "${profile}"`);
  }
}

const trustTotal = TRUST_COMPONENTS.reduce((a, c) => a + c.points, 0);
if (trustTotal !== 100) {
  throw new Error(`TrustScore components sum to ${trustTotal}, expected 100`);
}

// ---------------------------------------------------------------------------
// DISPLAY RULES (added v1.1)
//
// A metric that cannot be populated must be ABSENT FROM THE DOM — never
// rendered as a placeholder. This exists because a Ghanaian competitor ships
// fund pages whose Sharpe, Sortino, alpha, beta and drawdown fields render as
// "--" and "NaN%". An empty field reads as missing data; "NaN%" reads as
// broken software, and a product whose whole proposition is "trust the
// numbers" cannot afford to look broken.
//
// Enforced by the CI placeholder check. See ARCHITECTURE.md 15.2 and 16.3.
// ---------------------------------------------------------------------------

/** Any of these appearing in a rendered numeric field fails the build. */
export const PLACEHOLDER_BLOCKLIST = [
  "NaN", "Infinity", "-Infinity", "undefined", "null", "--", "—", "N/A", "n/a",
] as const;

export const DISPLAY_RULES = {
  /** Omit the row entirely rather than showing a placeholder. */
  OMIT_UNPOPULATED_METRICS: true,
  /** Every displayed figure must carry its verified_on date. */
  REQUIRE_VERIFIED_DATE: true,
  /**
   * The headline answers "what would I actually keep": gross yield less fees,
   * less withholding tax, less inflation. Nominal sits beneath it, greyed.
   * Showing a 20% nominal return in a 23% inflation year without the real
   * figure is close to misinformation, and no Ghanaian incumbent shows it.
   */
  HEADLINE_METRIC: "real_return_after_tax" as const,
  SECONDARY_METRIC: "annualised_return" as const,
  /** Always show the full bridge on the product page, never just the endpoint. */
  SHOW_YIELD_BRIDGE: true,
  /** Unscored products are still listed, with the reason shown. Never hidden. */
  SHOW_UNSCORED_WITH_REASON: true,
} as const;

/**
 * Guard for any numeric render path. Returns null when a metric must not be
 * displayed at all; callers omit the row on null rather than substituting text.
 */
export function displayableMetric(
  value: number | null | undefined,
  verifiedOn: string | null | undefined,
): { value: number; verifiedOn: string } | null {
  if (value === null || value === undefined) return null;
  if (!Number.isFinite(value)) return null;
  if (DISPLAY_RULES.REQUIRE_VERIFIED_DATE && !verifiedOn) return null;
  return { value, verifiedOn: verifiedOn as string };
}

export type ScoringConfig = {
  methodologyVersion: string;
  factors: typeof FACTORS;
  weights: typeof WEIGHTS;
  gates: typeof GATES;
  trustComponents: typeof TRUST_COMPONENTS;
  requiredSeries: typeof REQUIRED_SERIES;
  minPeerGroupSize: number;
  displayRules: typeof DISPLAY_RULES;
};

/** Serialised into every score_run row, so any rank is reproducible forever. */
export function buildScoringConfig(): ScoringConfig {
  return {
    methodologyVersion: METHODOLOGY_VERSION,
    factors: FACTORS,
    weights: WEIGHTS,
    gates: GATES,
    trustComponents: TRUST_COMPONENTS,
    requiredSeries: REQUIRED_SERIES,
    minPeerGroupSize: MIN_PEER_GROUP_SIZE,
    displayRules: DISPLAY_RULES,
  };
}
