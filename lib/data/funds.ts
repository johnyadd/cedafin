/**
 * lib/data/funds.ts — the query layer behind every fund-facing page.
 *
 * ONE RULE SHAPES THIS FILE: a number and its provenance travel together.
 * Every displayed figure carries the document it came from and the date it was
 * verified, because that is the product's entire differentiation (§4). A field
 * type of `number` invites a page to render a figure with no date attached; a
 * field type of `Sourced<number>` makes that impossible.
 *
 * WHAT IT DELIBERATELY DOES NOT DO
 *   - No scoring. Ranking needs peer groups of at least three
 *     (MIN_PEER_GROUP_SIZE) and no group here has that yet, so pages show
 *     factual comparison and no ranks.
 *   - No tax step. products.withholding_rate is null everywhere — the rates
 *     have not been verified with an accountant. The yield bridge therefore
 *     stops at inflation and marks the tax line as UNAVAILABLE rather than
 *     quietly skipping it, which would overstate what an investor keeps.
 *   - No chained level as a price. A `chained` series is an index, base 100,
 *     built from published monthly returns. Its LEVEL is meaningless as a unit
 *     price, so latestNav is null for those and the page must not invent one.
 */

import { publicClient } from "@/lib/supabase";

// ---------------------------------------------------------------------------
// Provenance-carrying value
// ---------------------------------------------------------------------------

export interface Sourced<T> {
  value: T;
  /** Date the figure refers to, not the date we fetched it. */
  asOf: string;
  /** Document title, e.g. "Stanbic_Cash_Trust_Fact_Sheet__2026-07.pdf". */
  source: string;
  /** First 12 chars of the SHA-256, enough to identify the exact file. */
  sourceHash: string | null;
}

export type Staleness = "current" | "ageing" | "stale";

/**
 * A computed return over a stated window.
 *
 * THE WINDOW IS NOT OPTIONAL CONTEXT — it is half the number. Stanbic Cash
 * Trust returned 36.88% over the year to February 2026, and 8% over the seven
 * months of 2026 on their own July factsheet. Both are true; they describe
 * different periods, and the first captures a bond recovery the second does
 * not. A return shown without its window is the kind of figure a fund's own
 * marketing prints, and doing that here would defeat the point of the site.
 *
 * realReturnPct is null unless the CPI series actually spanned the window.
 * compute_metrics.py withholds it rather than measuring a 2025 return against
 * 2026 inflation.
 */
export interface FundReturn {
  window: string;
  windowLabel: string;
  annualisedPct: number | null;
  totalPct: number | null;
  volatilityPct: number | null;
  maxDrawdownPct: number | null;
  realReturnPct: number | null;
  excessOverTbillPct: number | null;
  observationCount: number;
  coverage: number;
  /** Last observation in the window — what "to March 2026" refers to. */
  asOf: string;
}

/**
 * WHAT A CEDI HOLDER ACTUALLY EARNED ON GOLD.
 *
 * A fund's return is one number. Gold's is three, and any one alone misleads:
 *
 *   the metal, in dollars      +0.5%   June to August 2026
 *   the cedi against the USD   strengthened 11.735 -> 11.215
 *   what the holder got, in cedis  -3.9%
 *
 * Show only the last and gold looks like a poor investment. Show only the
 * first and it looks flat. What actually happened is that gold was fine and
 * the currency moved against the holder — the opposite of what gold is sold
 * to Ghanaians to do.
 *
 * AND THE PREMIUM COMES OFF THE TOP. Someone paying 7.75% above spot for a
 * quarter-ounce coin is 7.75% down before the price moves at all. Over three
 * months that dominates everything else, and a return figure ignoring it
 * describes an investment nobody made.
 */
export interface BullionReturn {
  from: string;
  to: string;
  /** Change in the cedi coin price — what the holder's coin is worth. */
  priceMovePct: number;
  /** Change in the dollar metal price — what gold itself did. */
  metalMovePct: number | null;
  /** Change in USD/GHS. Negative means the cedi strengthened. */
  fxMovePct: number | null;
  /** priceMovePct less the entry premium. What a CEDI holder is really up. */
  netOfPremiumPct: number | null;
  /**
   * metalMovePct less the entry premium — the same purchase judged in dollars.
   *
   * Both figures are true and they differ by the exchange rate. Someone paid
   * in cedis who will spend cedis has the first number. A diaspora Ghanaian
   * sending money home, or anyone holding gold because they distrust the
   * currency, has the second. Showing only one silently answers a question the
   * reader did not necessarily ask.
   */
  netOfPremiumUsdPct: number | null;
  /** The premium used, so the arithmetic can be checked. */
  premiumPct: number | null;
  days: number;
}

export interface FeePeriod {
  feeType: "management" | "custody" | "ter" | string;
  ratePct: number;
  effectiveFrom: string;
  effectiveTo: string | null;
  /** Last confirmation, not commencement. See RawFee.verified_on. */
  verifiedOn: string | null;
  /** Present on TER rows: says whether the figure is a full year or part-year. */
  conditions: string | null;
  source: string;
}

export interface FundRow {
  id: string;
  slug: string;
  name: string;
  shareClass: string;
  shareClassLabel: string | null;
  provider: { name: string; slug: string };
  assetClass: string | null;
  peerGroup: string | null;
  currency: string;
  distributes: boolean;

  /** Null for chained series — an index level is not a dealing price. */
  latestNav: Sourced<number> | null;
  seriesKind: "quoted" | "chained" | "adjusted";
  observationCount: number;
  firstObservation: string | null;
  lastObservation: string | null;
  staleness: Staleness;
  daysSinceLastObservation: number | null;

  minimumGhs: Sourced<number> | null;
  dealingFrequency: string | null;
  /** Fixed term in days, where a product has one. Bills do; funds do not. */
  lockInDays: number | null;

  currentManagementFeePct: Sourced<number> | null;
  currentCustodyFeePct: Sourced<number> | null;
  /**
   * Management plus custody, as disclosed. THE cross-provider cost figure:
   * FAAM publishes no expense ratio at all, so comparing Stanbic's TER against
   * FAAM's stated charges would compare two different things.
   */
  statedChargesPct: Sourced<number> | null;
  /**
   * Monthly closes, oldest first — for a sparkline, not for precision.
   *
   * A fund's NAV moves with performance AND distributions: a fund that pays
   * out drops on the distribution date, and the chart shows a fall that is not
   * a loss. The card says so beside it. Series shorter than ten points draw
   * nothing, because a line through six readings implies a trend the data
   * cannot carry.
   */
  priceSeries: number[];
  /** Present only for bullion. See BullionReturn. */
  bullionReturn: BullionReturn | null;
  /** "annual" | "on_purchase" | null — how statedChargesPct is levied. */
  chargeBasis: string | null;
  /** Tax treatment as the issuer publishes it. Not verified, not advice. */
  taxNote: string | null;
  /** NULL means not established — which is not the same as false. */
  shariaCompliant: boolean | null;
  /** Latest FULL-YEAR expense ratio. Part-year figures never land here. */
  lastFullYearTerPct: Sourced<number> | null;
  lastFullYearTerYear: number | null;
  /**
   * A part-year expense ratio, where one is published but no complete year has
   * elapsed. PDIF launched in October 2024 and its factsheets carry a
   * year-to-date figure, so "not published" was simply wrong — the fund
   * publishes it, there just isn't a full year yet. Distinct field so a page
   * can say "part-year only" rather than implying non-disclosure.
   */
  partYearTerPct: Sourced<number> | null;
  feeHistory: FeePeriod[];
  /** True when a fee changed within the observed window — worth surfacing. */
  feeChanged: boolean;

  /**
   * The most recent published yield, where the product quotes one. Distinct
   * from headlineReturn, which is derived from a price series — this is a rate
   * the issuer published, not something we calculated.
   */
  currentYield: Sourced<number> | null;
  /** Change in the quoted yield since the earliest observation held. */
  yieldChangePct: number | null;

  returns: FundReturn[];
  /** Longest window with a computed return — the headline figure. */
  headlineReturn: FundReturn | null;
}

// ---------------------------------------------------------------------------
// Freshness. Thresholds match the staleness policy in ARCHITECTURE.md §4.
// A number without a recent date is not information, it is decoration.
// ---------------------------------------------------------------------------

const AGEING_DAYS = 45;
const STALE_DAYS = 100;

export function stalenessOf(lastObservation: string | null): {
  staleness: Staleness;
  days: number | null;
} {
  if (!lastObservation) return { staleness: "stale", days: null };
  const days = Math.floor(
    (Date.now() - new Date(lastObservation + "T00:00:00Z").getTime()) / 86_400_000,
  );
  if (days <= AGEING_DAYS) return { staleness: "current", days };
  if (days <= STALE_DAYS) return { staleness: "ageing", days };
  return { staleness: "stale", days };
}

// ---------------------------------------------------------------------------
// Shape returned by the joined select
// ---------------------------------------------------------------------------

interface RawFee {
  fee_type: string;
  rate: number;
  effective_from: string;
  effective_to: string | null;
  /**
   * When the figure was LAST CONFIRMED, which is not when it took effect.
   * Stanbic Income Fund's fee has held since our records begin, so
   * effective_from is January 2024 — but the same figure appears in their July
   * 2026 factsheet. Showing a verification tick beside "1 Jan 2024" reads as
   * "nobody has checked this in two and a half years". The loader already
   * writes the latest confirmation here; the page just has to use it.
   */
  verified_on: string | null;
  conditions: string | null;
  sources: { title: string; content_sha256: string | null } | null;
}

const WINDOW_LABELS: Record<string, string> = {
  "1m": "1 month",
  "3m": "3 months",
  "6m": "6 months",
  "1y": "1 year",
  "3y": "3 years",
  "5y": "5 years",
};

// Longest first: a 3-year record says more than a 1-month one.
const WINDOW_RANK = ["5y", "3y", "1y", "6m", "3m", "1m"];

interface RawMetric {
  window_code: string;
  as_of: string;
  total_return: number | null;
  annualised_return: number | null;
  volatility: number | null;
  max_drawdown: number | null;
  real_return: number | null;
  excess_over_tbill: number | null;
  observation_count: number;
  coverage: number;
}

interface RawObs {
  as_of: string;
  nav: number | null;
  /**
   * A QUOTED RATE, not a computed return.
   *
   * Treasury bills and most Ghanaian money market funds publish a yield rather
   * than a unit price. There is no series to measure — the rate for the week
   * IS the figure, published by Bank of Ghana every Friday.
   *
   * Running it through a returns engine was the wrong instinct: 14 tenders of
   * perfectly good rates produced zero windows, because the engine is built to
   * derive returns from price movement and a rate series has none. The fix is
   * not more data, it is reading what is already there.
   */
  yield_annualised: number | null;
  /** LBMA gold in USD/oz for bullion — what the cedi price derives from. */
  reference_price: number | null;
  /** The USD/GHS rate used that day. */
  reference_fx: number | null;
  series_kind: string;
  sources: { title: string; content_sha256: string | null } | null;
}

interface RawProduct {
  id: string;
  slug: string;
  name: string;
  share_class: string;
  share_class_label: string | null;
  asset_class: string | null;
  peer_group: string | null;
  currency: string;
  distributes: boolean;
  dealing_frequency: string | null;
  lock_in_days: number | null;
  min_initial_minor: number | null;
  min_verified_on: string | null;
  tax_note: string | null;
  sharia_compliant: boolean | null;
  providers: { trading_name: string | null; legal_name: string; slug: string } | null;
  product_fees: RawFee[];
  nav_observations: RawObs[];
  product_metrics: RawMetric[];
}

const SELECT = `
  id, slug, name, share_class, share_class_label, asset_class, peer_group,
  currency, distributes, dealing_frequency, lock_in_days, min_initial_minor,
  min_verified_on, tax_note, sharia_compliant,
  providers ( trading_name, legal_name, slug ),
  product_fees ( fee_type, rate, effective_from, effective_to, verified_on,
                 conditions, sources ( title, content_sha256 ) ),
  nav_observations ( as_of, nav, yield_annualised, series_kind,
                     reference_price, reference_fx,
                     sources ( title, content_sha256 ) ),
  product_metrics ( window_code, as_of, total_return, annualised_return,
                    volatility, max_drawdown, real_return, excess_over_tbill,
                    observation_count, coverage )
`;

function sourced<T>(
  value: T | null | undefined,
  asOf: string | null | undefined,
  src: { title: string; content_sha256: string | null } | null | undefined,
): Sourced<T> | null {
  // No date means no publication. This is the guard that keeps an undated
  // figure off a page — the failure a Ghanaian competitor ships today.
  if (value === null || value === undefined || !asOf) return null;
  return {
    value,
    asOf,
    source: src?.title ?? "unverified",
    sourceHash: src?.content_sha256?.slice(0, 12) ?? null,
  };
}

function currentFee(fees: RawFee[], type: string): RawFee | null {
  const today = new Date().toISOString().slice(0, 10);
  const live = fees
    .filter((f) => f.fee_type === type)
    .filter((f) => f.effective_from <= today)
    .filter((f) => !f.effective_to || f.effective_to >= today)
    .sort((a, b) => b.effective_from.localeCompare(a.effective_from));
  return live[0] ?? null;
}

/**
 * The latest expense ratio that covers a COMPLETE year. Part-year figures are
 * excluded on purpose: the factsheets publish a year-to-date number that
 * climbs through each year, so a June figure understates the annual cost by
 * roughly half. The loader marks full years in `conditions`; this trusts that
 * marking rather than re-deriving it.
 */
function partYearTer(fees: RawFee[]): RawFee | null {
  return (
    fees
      .filter((f) => f.fee_type === "ter")
      .filter((f) => /PART-YEAR/i.test(f.conditions ?? ""))
      .sort((a, b) => b.effective_from.localeCompare(a.effective_from))[0] ?? null
  );
}

function lastFullYearTer(fees: RawFee[]): { fee: RawFee; year: number } | null {
  const complete = fees
    .filter((f) => f.fee_type === "ter" && f.effective_to)
    .filter((f) => !/PART-YEAR/i.test(f.conditions ?? ""))
    .sort((a, b) => b.effective_from.localeCompare(a.effective_from));
  if (!complete[0]) return null;
  return { fee: complete[0], year: Number(complete[0].effective_from.slice(0, 4)) };
}

function toFundRow(p: RawProduct): FundRow {
  const obs = [...(p.nav_observations ?? [])].sort((a, b) =>
    a.as_of.localeCompare(b.as_of),
  );
  const last = obs[obs.length - 1] ?? null;
  const kind = (last?.series_kind ?? "quoted") as FundRow["seriesKind"];
  const { staleness, days } = stalenessOf(last?.as_of ?? null);

  const yields = obs.filter((o) => o.yield_annualised !== null);
  const latestYield = yields[yields.length - 1] ?? null;
  const firstYield = yields[0] ?? null;

  const mgmt = currentFee(p.product_fees ?? [], "management");
  const cust = currentFee(p.product_fees ?? [], "custody");
  const ter = lastFullYearTer(p.product_fees ?? []);
  const stated = currentFee(p.product_fees ?? [], "stated_charges");

  /**
   * A COST IS A COST, WHATEVER IT IS CALLED.
   *
   * The Ghana Gold Coin has no management fee and no custody fee, so the usual
   * management-plus-custody sum returns nothing and the comparison page said
   * "Charges not published" — beside a fund at 1.75%, implying gold is free to
   * own. It is not. Bank of Ghana sells an ounce for about 3.5% more than the
   * metal is worth at LBMA spot times the day's exchange rate, and a
   * quarter-ounce coin for 7.75% more. That is the cost of ownership; it is
   * simply charged once on purchase rather than annually.
   *
   * The denomination penalty is added on top for the smaller coins, because
   * the person buying a quarter ounce pays BOTH — the base premium and the
   * extra for buying in pieces. Reporting only one would understate what the
   * smallest buyer actually pays, which is the opposite of what this site is
   * for.
   *
   * The distinction between a recurring charge and a one-off is real and
   * matters, so it is carried in chargeBasis rather than hidden — but showing
   * nothing at all was the worse error.
   */
  const premium = currentFee(p.product_fees ?? [], "premium_over_spot");
  const denomPenalty = currentFee(p.product_fees ?? [], "denomination_penalty");
  const bullionCost =
    premium
      ? {
          rate: premium.rate + (denomPenalty?.rate ?? 0),
          verified_on: premium.verified_on,
          effective_from: premium.effective_from,
          sources: premium.sources,
        }
      : null;
  const partial = partYearTer(p.product_fees ?? []);

  const history: FeePeriod[] = (p.product_fees ?? [])
    .map((f) => ({
      feeType: f.fee_type,
      ratePct: Number((f.rate * 100).toFixed(4)),
      effectiveFrom: f.effective_from,
      effectiveTo: f.effective_to,
      verifiedOn: f.verified_on,
      conditions: f.conditions,
      source: f.sources?.title ?? "unverified",
    }))
    .sort(
      (a, b) =>
        a.feeType.localeCompare(b.feeType) ||
        a.effectiveFrom.localeCompare(b.effectiveFrom),
    );

  const pct = (v: number | null | undefined) =>
    v === null || v === undefined ? null : Number((v * 100).toFixed(2));

  const returns: FundReturn[] = (p.product_metrics ?? [])
    .map((m) => ({
      window: m.window_code,
      windowLabel: WINDOW_LABELS[m.window_code] ?? m.window_code,
      annualisedPct: pct(m.annualised_return),
      totalPct: pct(m.total_return),
      volatilityPct: pct(m.volatility),
      maxDrawdownPct: pct(m.max_drawdown),
      realReturnPct: pct(m.real_return),
      excessOverTbillPct: pct(m.excess_over_tbill),
      observationCount: m.observation_count,
      coverage: m.coverage,
      asOf: m.as_of,
    }))
    .sort(
      (a, b) => WINDOW_RANK.indexOf(a.window) - WINDOW_RANK.indexOf(b.window),
    );

  const feeChanged =
    ["management", "custody"].some(
      (t) => history.filter((h) => h.feeType === t).length > 1,
    );

  return {
    id: p.id,
    slug: p.slug,
    name: p.name,
    shareClass: p.share_class,
    shareClassLabel: p.share_class_label,
    provider: {
      name: p.providers?.trading_name ?? p.providers?.legal_name ?? "Unknown",
      slug: p.providers?.slug ?? "",
    },
    assetClass: p.asset_class,
    peerGroup: p.peer_group,
    currency: p.currency,
    distributes: p.distributes,

    // A chained level is an index, not a price. Never surface it as a NAV.
    latestNav:
      kind === "quoted" ? sourced(last?.nav ?? null, last?.as_of, last?.sources) : null,
    seriesKind: kind,
    observationCount: obs.length,
    firstObservation: obs[0]?.as_of ?? null,
    lastObservation: last?.as_of ?? null,
    staleness,
    daysSinceLastObservation: days,

    minimumGhs:
      p.min_initial_minor !== null
        ? sourced(p.min_initial_minor / 100, p.min_verified_on, last?.sources)
        : null,
    dealingFrequency: p.dealing_frequency,
    lockInDays: p.lock_in_days ?? null,
    taxNote: (p.tax_note as string | null) ?? null,
    shariaCompliant: (p.sharia_compliant as boolean | null) ?? null,

    currentManagementFeePct: mgmt
      ? sourced(
          Number((mgmt.rate * 100).toFixed(4)),
          mgmt.verified_on ?? mgmt.effective_from,
          mgmt.sources,
        )
      : null,
    currentCustodyFeePct: cust
      ? sourced(
          Number((cust.rate * 100).toFixed(4)),
          cust.verified_on ?? cust.effective_from,
          cust.sources,
        )
      : null,
    // Treasury bills quote a yield, not a price — their observations carry
    // yield_annualised and no nav, so a nav-only series left them blank while
    // every other product on the page had a line. Same chart, different
    // quantity: for a bill it plots the rate, which is what moves.
    priceSeries: obs
      .map((o) =>
        o.nav !== null
          ? o.nav
          : o.yield_annualised !== null
            ? o.yield_annualised * 100
            : null,
      )
      .filter((v): v is number => v !== null),
    bullionReturn: (() => {
      // Only bullion carries a reference price, so this is null everywhere
      // else without needing to test the asset class.
      const withRef = obs.filter(
        (o) => o.nav !== null && o.reference_price !== null,
      );
      if (withRef.length < 2) return null;
      const a = withRef[0];
      const b = withRef[withRef.length - 1];
      const days = Math.round(
        (new Date(b.as_of).getTime() - new Date(a.as_of).getTime()) / 86_400_000,
      );
      if (days < 14) return null;

      const priceMove = ((b.nav! - a.nav!) / a.nav!) * 100;
      const metalMove =
        ((b.reference_price! - a.reference_price!) / a.reference_price!) * 100;
      const fxMove =
        a.reference_fx && b.reference_fx
          ? ((b.reference_fx - a.reference_fx) / a.reference_fx) * 100
          : null;
      const prem = premium
        ? (premium.rate + (denomPenalty?.rate ?? 0)) * 100
        : null;

      return {
        from: a.as_of,
        to: b.as_of,
        priceMovePct: Number(priceMove.toFixed(2)),
        metalMovePct: Number(metalMove.toFixed(2)),
        fxMovePct: fxMove === null ? null : Number(fxMove.toFixed(2)),
        // Straight subtraction, not compounding: the premium is paid once at
        // entry, so it comes off the gain rather than accruing.
        netOfPremiumPct:
          prem === null ? null : Number((priceMove - prem).toFixed(2)),
        netOfPremiumUsdPct:
          prem === null ? null : Number((metalMove - prem).toFixed(2)),
        premiumPct: prem === null ? null : Number(prem.toFixed(2)),
        days,
      };
    })(),
    statedChargesPct: stated
      ? sourced(
          Number((stated.rate * 100).toFixed(4)),
          stated.verified_on ?? stated.effective_from,
          stated.sources,
        )
      : bullionCost
        ? sourced(
            Number((bullionCost.rate * 100).toFixed(4)),
            bullionCost.verified_on ?? bullionCost.effective_from,
            bullionCost.sources,
          )
        : null,
    /**
     * How the cost above is levied. "annual" for a fund's management charge;
     * "on_purchase" for a bullion premium paid once. A page that shows 7.75%
     * beside 1.75% without saying one is annual and the other is not would
     * mislead in the other direction.
     */
    chargeBasis: stated ? "annual" : bullionCost ? "on_purchase" : null,
    lastFullYearTerPct: ter
      ? sourced(
          Number((ter.fee.rate * 100).toFixed(4)),
          ter.fee.verified_on ?? ter.fee.effective_to,
          ter.fee.sources,
        )
      : null,
    lastFullYearTerYear: ter?.year ?? null,
    partYearTerPct: partial
      ? sourced(
          Number((partial.rate * 100).toFixed(4)),
          partial.verified_on ?? partial.effective_from,
          partial.sources,
        )
      : null,
    feeHistory: history,
    feeChanged,
    currentYield: latestYield
      ? sourced(
          Number((latestYield.yield_annualised! * 100).toFixed(4)),
          latestYield.as_of,
          latestYield.sources,
        )
      : null,
    yieldChangePct:
      latestYield && firstYield && yields.length > 1
        ? Number(
            (
              (latestYield.yield_annualised! - firstYield.yield_annualised!) * 100
            ).toFixed(2),
          )
        : null,

    returns,
    // The longest window with an actual figure. A fund with 25 months of data
    // says more with its 1-year number than its 1-month one.
    headlineReturn: returns.find((r) => r.annualisedPct !== null) ?? null,
  };
}

// ---------------------------------------------------------------------------
// Public queries
// ---------------------------------------------------------------------------

/**
 * A directory entry: a fund known to exist, with no verified figures yet.
 *
 * These are the 67 funds catalogued from a third-party aggregator. They carry a
 * name, a probable provider and sometimes a category — and nothing else. They
 * are `status='draft'` so they can never reach a comparison page and appear to
 * have no charges; absent is not free.
 *
 * The name is NOT verified against the SEC register. The catalogue's own slugs
 * carry "formerly" markers, which is evidence enough that fund names move.
 * Anything user-facing must say so, and anything provider-facing must be
 * checked first — getting a manager's own fund name wrong in a first approach
 * undoes exactly the credibility the listing is meant to build.
 */
export interface DirectoryEntry {
  id: string;
  slug: string;
  name: string;
  assetClass: string | null;
  /** What the catalogue knows exists but we have not obtained. */
  note: string | null;
  nameVerified: false;
}

export async function getDirectory(): Promise<DirectoryEntry[]> {
  const { data, error } = await publicClient()
    .from("products")
    .select("id, slug, name, asset_class, objective, status")
    .eq("status", "draft")
    .eq("market_side", "invest")

    .like("slug", "cat-%")
    .order("name");
  if (error) throw new Error(`getDirectory: ${error.message}`);
  return (data ?? []).map((d: Record<string, unknown>) => ({
    id: String(d.id),
    slug: String(d.slug),
    name: String(d.name),
    assetClass: (d.asset_class as string | null) ?? null,
    note: (d.objective as string | null) ?? null,
    nameVerified: false as const,
  }));
}

/**
 * A lending product: one bank, one credit category, one tenor.
 *
 * TWO RATES, NOT A RANGE. Bank of Ghana publishes an average lending rate and
 * an average APR per bank per table. The gap between them is fees —
 * Agricultural Development Bank lends at 19.59% and costs 28.13%, an 8.5 point
 * difference in charges alone, while Access Bank's gap is 0.03. A borrower
 * comparing advertised rates would rank those two as near-identical.
 *
 * INDICATIVE, ALWAYS. BoG states that a typical customer may face a different
 * APR after the bank assesses them. That caveat is stored per product and must
 * appear wherever a rate does — publishing 11.03% as what a business WILL get
 * would be wrong in the direction that costs someone money.
 */
export interface LendingRow {
  id: string;
  slug: string;
  name: string;
  category: "personal_credit" | "sme_credit" | "corporate_credit" | string;
  tenorYears: number;
  provider: { name: string; slug: string };
  /** The advertised lending rate — what a bank leads with. */
  lendingRatePct: number | null;
  /** The APR — lending rate plus every charge. What it actually costs. */
  aprPct: number | null;
  /** aprPct - lendingRatePct. The fees a headline rate hides. */
  feeGapPct: number | null;
  /** BoG's own wording on why this is not a quote. */
  caveat: string | null;
  asOf: string | null;
}

const CREDIT_LABEL: Record<string, string> = {
  personal_credit: "Personal",
  sme_credit: "SME",
  corporate_credit: "Corporate",
};

export function creditLabel(c: string): string {
  return CREDIT_LABEL[c] ?? c;
}

export async function getLending(
  category?: string,
  /*
    Filter to one provider in the QUERY.

    Without it the lender page fetched all 157 lending products and kept
    seven — once per page, twenty-three times in a build, which truncated
    the response mid-stream and failed with a garbled parse error.
  */
  providerSlug?: string,
): Promise<LendingRow[]> {
  let q = publicClient()
    .from("products")
    .select(
      `id, slug, name, asset_class, lock_in_days, rate_min, rate_max,
       eligibility_notes,
       providers!inner ( trading_name, legal_name, slug ),
       product_fees ( verified_on )`,
    )
    .eq("market_side", "borrow")
    .eq("status", "published");
  if (category) q = q.eq("asset_class", category);
  if (providerSlug) q = q.eq("providers.slug", providerSlug);

  const { data, error } = await q;
  if (error) throw new Error(`getLending: ${error.message}`);

  const pct = (v: number | null | undefined) =>
    v === null || v === undefined ? null : Number((v * 100).toFixed(2));

  return (data ?? [])
    .map((d: Record<string, unknown>) => {
      const prov = d.providers as
        | { trading_name: string | null; legal_name: string; slug: string }
        | null;
      const lending = pct(d.rate_min as number | null);
      const apr = pct(d.rate_max as number | null);
      const fees = (d.product_fees ?? []) as { verified_on: string }[];
      return {
        id: String(d.id),
        slug: String(d.slug),
        name: String(d.name),
        category: String(d.asset_class),
        tenorYears: Math.round(((d.lock_in_days as number) ?? 365) / 365),
        provider: {
          name: prov?.trading_name ?? prov?.legal_name ?? "Unknown",
          slug: prov?.slug ?? "",
        },
        lendingRatePct: lending,
        aprPct: apr,
        feeGapPct:
          lending !== null && apr !== null
            ? Number((apr - lending).toFixed(2))
            : null,
        caveat: (d.eligibility_notes as string | null) ?? null,
        asOf: fees[0]?.verified_on ?? null,
      };
    })
    .sort((a, b) => (a.aprPct ?? 999) - (b.aprPct ?? 999));
}

/**
 * A lender and everything held about them.
 *
 * WHAT THIS PAGE IS FOR: a bank opening it should see immediately that we
 * publish their Bank of Ghana average and nothing about their actual products
 * — no facility name, no minimum, no security requirement, no turnaround. All
 * seven product fields are blank for all 23 banks, and saying so plainly is
 * what makes the ask credible.
 *
 * A REGULATORY AVERAGE IS NOT A PRODUCT. GCB does not sell "one-year SME
 * credit at 22.3%" — it sells named facilities with terms. The average is a
 * supervisory statistic. A page implying otherwise would misrepresent both the
 * bank and what a borrower can get.
 */
export interface LenderProfile {
  slug: string;
  name: string;
  legalName: string;
  website: string | null;
  contactEmail: string | null;
  officeAddress: string | null;
  products: LendingRow[];
  /** Cheapest all-in rate they report, across all categories. */
  bestApr: number | null;
  /** Largest gap between their advertised rate and true cost. */
  widestFeeGap: number | null;
  /** Of the product details a borrower needs, which we hold. */
  disclosed: { field: string; has: boolean }[];
  asOf: string | null;
}

/**
 * Deliberately all-blank today. These are PRODUCT facts, and BoG's APR report
 * contains none of them — it reports averages for supervision, not terms for
 * sale. Listing them as missing is the entire point of the page.
 */
const LENDER_FIELDS = [
  "Facility name",
  "Minimum advance",
  "Maximum advance",
  "Security required",
  "Who qualifies",
  "Decision turnaround",
  "Actual rate range",
];

export async function getLender(slug: string): Promise<LenderProfile | null> {
  const { data, error } = await publicClient()
    .from("providers")
    .select(
      `slug, trading_name, legal_name, website, contact_email, office_address`,
    )
    .eq("slug", slug)
    .maybeSingle();
  if (error) throw new Error(`getLender: ${error.message}`);
  if (!data) return null;

  /*
    Filtered in the query, not after it.

    This fetched every lending product in the market and then kept one
    provider's — 157 rows to use seven, once per lender page, twenty-three
    times in a build. Enough to truncate the response mid-stream and fail
    with a garbled parse error.

    getLending already accepts a providerSlug. It simply was not being used.
  */
  const mine = await getLending(undefined, slug);
  if (mine.length === 0) return null;

  const aprs = mine.map((r) => r.aprPct).filter((v): v is number => v !== null);
  const gaps = mine
    .map((r) => r.feeGapPct)
    .filter((v): v is number => v !== null);

  return {
    slug: String(data.slug),
    name: String(data.trading_name ?? data.legal_name ?? slug),
    legalName: String(data.legal_name ?? ""),
    website: (data.website as string | null) ?? null,
    contactEmail: (data.contact_email as string | null) ?? null,
    officeAddress: (data.office_address as string | null) ?? null,
    products: mine,
    bestApr: aprs.length ? Math.min(...aprs) : null,
    widestFeeGap: gaps.length ? Math.max(...gaps) : null,
    // Every one false, until a lender tells us otherwise.
    disclosed: LENDER_FIELDS.map((field) => ({ field, has: false })),
    asOf: mine.find((r) => r.asOf)?.asOf ?? null,
  };
}

export async function getLenderSlugs(): Promise<string[]> {
  const all = await getLending();
  return [...new Set(all.map((r) => r.provider.slug))].filter(Boolean);
}

/** Market average APR per category and tenor, for context on a lender page. */
/**
 * Market average APR per category and tenor, for context on a lender page.
 *
 * Its own slim query rather than getLending().
 *
 * getLending returns the full payload — eligibility notes, provider records,
 * fee histories — and this runs once per lender page, twenty-three times in a
 * build. That was enough to truncate the response mid-stream and fail the
 * build with a garbled parse error.
 *
 * Three columns is all an average needs.
 */
export async function getMarketAverages(): Promise<
  Map<string, { avg: number; count: number }>
> {
  const { data, error } = await publicClient()
    .from("products")
    .select("asset_class, lock_in_days, rate_min, rate_max")
    .eq("market_side", "borrow")
    .eq("status", "published");
  if (error) throw new Error(`getMarketAverages: ${error.message}`);

  const buckets = new Map<string, number[]>();
  for (const r of (data ?? []) as {
    asset_class: string | null;
    lock_in_days: number | null;
    rate_min: number | null;
    rate_max: number | null;
  }[]) {
    // The APR shown elsewhere is the maximum — what the loan can cost — so
    // the average is of those, not of the advertised minimums.
    const apr = r.rate_max ?? r.rate_min;
    if (apr === null || !r.asset_class || !r.lock_in_days) continue;
    const years = Math.round(r.lock_in_days / 365);
    const k = `${r.asset_class}:${years}`;
    if (!buckets.has(k)) buckets.set(k, []);
    buckets.get(k)!.push(Number((apr * 100).toFixed(2)));
  }

  const out = new Map<string, { avg: number; count: number }>();
  for (const [k, vals] of buckets) {
    out.set(k, {
      avg: Number((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2)),
      count: vals.length,
    });
  }
  return out;
}

/* ────────────────────────────────────────────────────────────────────────
   MATCHING: what someone said they want, against what exists.

   TWO OUTPUTS FROM ONE SET OF ANSWERS, and the line between them is
   regulatory, not technical.

     FILTER      narrows on criteria the user stated. "I have GH¢500, I may
                 need it within a month, I want money market" excludes a fund
                 with a GH¢1,000 minimum. That is arithmetic on facts they
                 supplied, and needs no licence.

     RECOMMENDER forms a judgement about the person — that their age implies a
                 horizon, that their stated risk tolerance contradicts their
                 asset preference, that one product suits them better. That is
                 advice. It is built, and it stays behind COMPLIANCE_PHASE
                 until there is a licence to give it.

   The distinction is not cosmetic. Applying a user's own criteria is
   different from telling them what they should do, and a site that blurs the
   two while unlicensed is misrepresenting itself to people making decisions
   about their savings.
   ──────────────────────────────────────────────────────────────────────── */

export interface InvestorAnswers {
  ageBand?: "under25" | "25to34" | "35to49" | "50to64" | "65plus";
  amountGhs?: number;
  regularContribution?: boolean;
  /** How soon they may need the money back. Drives dealing frequency. */
  horizon?: "under3m" | "3to12m" | "1to3y" | "3to5y" | "over5y";
  purpose?: "emergency" | "house" | "school" | "retirement" | "growth" | "other";
  /**
   * BEHAVIOURAL, NOT SELF-RATED. "How would you react if it fell 20%" gets a
   * truer answer than "rate your risk appetite", which almost everyone
   * overstates until it happens.
   */
  dropReaction?: "sell" | "worry" | "hold" | "buymore";
  assetPreference?: string[];
  hasExisting?: boolean;
  currency?: "GHS" | "USD" | "other";
}

export interface MatchResult {
  fund: FundRow;
  /** Every criterion the user stated that this fund satisfies. */
  meets: string[];
  /** Criteria that could not be checked, and why. */
  unchecked: string[];
}

export interface MatchOutcome {
  matches: MatchResult[];
  /** Funds excluded, with the reason — never silently dropped. */
  excluded: { fund: FundRow; because: string }[];
  /** What no product could be filtered on, because nobody publishes it. */
  notFilterable: string[];
  /** Contradictions in the answers themselves. Shown, not resolved for them. */
  conflicts: string[];
  totalConsidered: number;
}

/** Horizon in days, for comparing against dealing frequency and lock-ins. */
const HORIZON_DAYS: Record<string, number> = {
  under3m: 90,
  "3to12m": 365,
  "1to3y": 1095,
  "3to5y": 1825,
  over5y: 3650,
};

/** How quickly money can be taken out, in days. */
const DEALING_DAYS: Record<string, number> = {
  daily: 1,
  weekly: 7,
  monthly: 30,
  quarterly: 90,
  at_maturity: 365,
  on_application: 30,
};

/** Rough volatility ordering, for flagging answer contradictions only. */
const ASSET_RISK: Record<string, number> = {
  government_security: 1,
  money_market: 2,
  fixed_income: 3,
  deposit: 1,
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

export function matchFunds(
  funds: FundRow[],
  a: InvestorAnswers,
): MatchOutcome {
  const matches: MatchResult[] = [];
  const excluded: { fund: FundRow; because: string }[] = [];
  const conflicts: string[] = [];

  // A stated asset preference and a stated reaction to a fall can contradict
  // each other. Neither is overridden — the person is told, and decides.
  if (a.dropReaction && a.assetPreference?.length) {
    const ceiling = REACTION_CEILING[a.dropReaction] ?? 5;
    const tooRisky = a.assetPreference.filter(
      (c) => (ASSET_RISK[c] ?? 3) > ceiling,
    );
    if (tooRisky.length) {
      conflicts.push(
        `You said you'd ${
          a.dropReaction === "sell" ? "sell" : "be worried"
        } if your investment fell 20%, but you've asked to see ${tooRisky
          .map((c) => c.replace(/_/g, " "))
          .join(" and ")} funds, where falls like that are normal. Both are
         shown — worth knowing they pull in different directions.`.replace(
          /\s+/g,
          " ",
        ),
      );
    }
  }
  if (a.horizon === "under3m" && a.assetPreference?.includes("equity")) {
    conflicts.push(
      "Equity funds are usually held for years, not months. Over three months, " +
        "what the market does matters more than what the fund does.",
    );
  }

  for (const f of funds) {
    const meets: string[] = [];
    const unchecked: string[] = [];

    if (a.currency && f.currency && f.currency !== a.currency) {
      excluded.push({ fund: f, because: `priced in ${f.currency}` });
      continue;
    }

    if (a.assetPreference?.length) {
      if (!a.assetPreference.includes(f.assetClass ?? "")) {
        excluded.push({
          fund: f,
          because: `${(f.assetClass ?? "unclassified").replace(/_/g, " ")}, not among the types you chose`,
        });
        continue;
      }
      meets.push("the type of fund you asked for");
    }

    if (a.amountGhs !== undefined) {
      const min = f.minimumGhs?.value;
      if (min === undefined || min === null) {
        unchecked.push("minimum investment — this provider doesn't publish one");
      } else if (min > a.amountGhs) {
        excluded.push({
          fund: f,
          because: `needs at least ${GHS_MIN.format(min)} to start`,
        });
        continue;
      } else {
        meets.push(`takes ${GHS_MIN.format(a.amountGhs)} to start`);
      }
    }

    if (a.horizon) {
      const want = HORIZON_DAYS[a.horizon] ?? 365;
      const lock = f.lockInDays ?? 0;
      const dealing = f.dealingFrequency
        ? (DEALING_DAYS[f.dealingFrequency] ?? 30)
        : null;

      if (lock > want) {
        excluded.push({
          fund: f,
          because: `locks your money for ${lock} days, longer than you said`,
        });
        continue;
      }
      if (dealing === null) {
        unchecked.push("how quickly you can withdraw — not published");
      } else if (dealing <= want) {
        meets.push(
          dealing <= 1
            ? "you can take money out any working day"
            : `money back within about ${dealing} days`,
        );
      }
    }

    matches.push({ fund: f, meets, unchecked });
  }

  // Cheapest first. Cost is the one thing we can compare across every fund,
  // and it is the only ordering that cannot be gamed by a provider.
  matches.sort((x, y) => {
    const a1 = x.fund.statedChargesPct?.value ?? Number.POSITIVE_INFINITY;
    const b1 = y.fund.statedChargesPct?.value ?? Number.POSITIVE_INFINITY;
    return a1 - b1 || x.fund.name.localeCompare(y.fund.name);
  });

  // Answers we collected but cannot act on, because no provider publishes
  // anything to match them against. Saying so is more useful than pretending
  // the question shaped the result.
  const notFilterable: string[] = [];
  if (a.ageBand) notFilterable.push("your age");
  if (a.purpose) notFilterable.push("what you're saving for");
  if (a.regularContribution !== undefined)
    notFilterable.push("whether you'll add to it regularly");
  if (a.hasExisting !== undefined)
    notFilterable.push("what you already hold");

  return {
    matches,
    excluded,
    notFilterable,
    conflicts,
    totalConsidered: funds.length,
  };
}

const GHS_MIN = new Intl.NumberFormat("en-GH", {
  style: "currency",
  currency: "GHS",
  maximumFractionDigits: 0,
});

/**
 * A licensed dealing member of the Ghana Stock Exchange.
 *
 * The only comparable public fact about Ghanaian stockbrokers is how much
 * business they do. Not one of the twenty-four publishes a commission rate, so
 * a saver choosing where to open an account has nothing to go on — which is
 * why this is published despite being a poor proxy for anything a saver
 * actually wants to know.
 *
 * THE RANGE IS NOT OPTIONAL. IC Securities averages 52.70% of value traded and
 * ranges from 19.97% to 78.82% across fifteen months. Show the maximum and the
 * exchange looks captured; show the average and it looks like comfortable
 * leadership. Neither is true. A fifty-nine point swing with no trend means a
 * few block trades decide who leads in any month — a fact about how thin the
 * market is, not about any firm's position.
 */
export interface BrokerRow {
  slug: string;
  name: string;
  avgSharePct: number | null;
  minSharePct: number | null;
  maxSharePct: number | null;
  monthsObserved: number | null;
  firstSeen: string | null;
  lastSeen: string | null;
  /**
   * From the SEC's broker-dealer register. A page listing who trades most and
   * giving no way to reach any of them tells a saver the least useful half of
   * what it knows.
   */
  website: string | null;
  contactEmail: string | null;
  contactPhone: string | null;
  officeAddress: string | null;
  /** The SEC's name for the firm, which differs from the exchange's. */
  legalName: string | null;
  /**
   * Share of VOLUME, read against share of value.
   *
   * IC Securities: 78.82% of value, 62.16% of volume — fewer, larger trades.
   * Databank: 3.32% of value, 7.77% of volume — more trades, smaller ones.
   *
   * Nobody publishes whether a Ghanaian broker wants a GH¢5,000 order. This is
   * the closest the public data comes to answering it, and it points the
   * opposite way to the value ranking — which is exactly why showing value
   * alone was inadequate.
   */
  volumeSharePct: number | null;
  /** Cedis and shares traded in the latest month, so a percentage has a size. */
  valueTradedGhs: number | null;
  volumeTraded: number | null;
  latestMonth: string | null;
}

export async function getBrokers(): Promise<BrokerRow[]> {
  const { data, error } = await publicClient()
    .from("providers")
    .select(
      `slug, trading_name, legal_name, broker_share_avg_pct,
       broker_share_min_pct, broker_share_max_pct, broker_months_observed,
       broker_first_seen, broker_last_seen,
       broker_volume_share_avg_pct, broker_value_traded_ghs,
       broker_volume_traded, broker_latest_month,
       website, contact_email, contact_phone, office_address`,
    )
    .like("slug", "broker-%")
    .eq("status", "published");
  if (error) throw new Error(`getBrokers: ${error.message}`);

  return (data ?? [])
    .map((d: Record<string, unknown>) => ({
      slug: String(d.slug),
      name: String(d.trading_name ?? d.legal_name ?? d.slug),
      avgSharePct: (d.broker_share_avg_pct as number | null) ?? null,
      minSharePct: (d.broker_share_min_pct as number | null) ?? null,
      maxSharePct: (d.broker_share_max_pct as number | null) ?? null,
      monthsObserved: (d.broker_months_observed as number | null) ?? null,
      firstSeen: (d.broker_first_seen as string | null) ?? null,
      lastSeen: (d.broker_last_seen as string | null) ?? null,
      website: (d.website as string | null) ?? null,
      contactEmail: (d.contact_email as string | null) ?? null,
      contactPhone: (d.contact_phone as string | null) ?? null,
      officeAddress: (d.office_address as string | null) ?? null,
      legalName: (d.legal_name as string | null) ?? null,
      volumeSharePct: (d.broker_volume_share_avg_pct as number | null) ?? null,
      valueTradedGhs: (d.broker_value_traded_ghs as number | null) ?? null,
      volumeTraded: (d.broker_volume_traded as number | null) ?? null,
      latestMonth: (d.broker_latest_month as string | null) ?? null,
    }))
    .sort((a, b) => (b.avgSharePct ?? -1) - (a.avgSharePct ?? -1));
}

/**
 * A listed Ghanaian share, with its monthly closing prices.
 *
 * PRICE MOVE, NOT TOTAL RETURN. Dividends are excluded because the exchange
 * does not publish them — its glossary defines dividend yield and prints it
 * for no company. So every figure here understates what a holder received,
 * and the page says so rather than presenting a partial number as complete.
 */
export interface EquityRow {
  slug: string;
  ticker: string;
  sector: string;
  latestPrice: number | null;
  /** Monthly closes, oldest first — enough for shape, not for precision. */
  prices: number[];
  priceMovePct: number | null;
  months: number;
  firstSeen: string | null;
  lastSeen: string | null;
  marketCapGhsMil: number | null;
  peRatio: number | null;
}

export async function getEquities(): Promise<EquityRow[]> {
  const { data, error } = await publicClient()
    .from("products")
    .select(
      `slug, name, asset_class,
       nav_observations ( as_of, nav )`,
    )
    .eq("market_side", "invest")

    .eq("asset_class", "equity")
    .eq("status", "published");
  if (error) throw new Error(`getEquities: ${error.message}`);

  return (data ?? [])
    .map((d: Record<string, unknown>) => {
      const obs = [...((d.nav_observations ?? []) as { as_of: string; nav: number | null }[])]
        .filter((o) => o.nav !== null)
        .sort((a, b) => a.as_of.localeCompare(b.as_of));
      const prices = obs.map((o) => o.nav as number);
      const name = String(d.name);
      // Stored as "TICKER · Sector".
      const [ticker, sector] = name.split("·").map((x) => x.trim());
      const move =
        prices.length >= 2 && prices[0] > 0
          ? Number(((prices[prices.length - 1] / prices[0] - 1) * 100).toFixed(2))
          : null;
      return {
        slug: String(d.slug),
        ticker: ticker || name,
        sector: sector || "Listed",
        latestPrice: prices.length ? prices[prices.length - 1] : null,
        prices,
        priceMovePct: move,
        months: prices.length,
        firstSeen: obs[0]?.as_of ?? null,
        lastSeen: obs[obs.length - 1]?.as_of ?? null,
        // Not stored per-observation; left null rather than invented.
        marketCapGhsMil: null,
        peRatio: null,
      };
    })
    .sort((a, b) => (b.priceMovePct ?? -999) - (a.priceMovePct ?? -999));
}

export async function getPublishedFunds(): Promise<FundRow[]> {
  const { data, error } = await publicClient()
    .from("products")
    .select(SELECT)
    .eq("status", "published")

    // Lending products live in the same table. Without this the fund
    // counts absorb 157 bank facilities and the home page claims to
    // track 232 funds when it tracks 72 — a false number sitting three
    // inches above "gaps are shown, not hidden".
    .eq("market_side", "invest")

    .order("name");
  if (error) throw new Error(`getPublishedFunds: ${error.message}`);
  return (data as unknown as RawProduct[]).map(toFundRow);
}

export async function getFundsByPeerGroup(peerGroup: string): Promise<FundRow[]> {
  const { data, error } = await publicClient()
    .from("products")
    .select(SELECT)
    .eq("status", "published")
    .eq("peer_group", peerGroup)
    .order("name");
  if (error) throw new Error(`getFundsByPeerGroup: ${error.message}`);
  return (data as unknown as RawProduct[]).map(toFundRow);
}

export interface PeerGroupSummary {
  peerGroup: string;
  label: string;
  /** DISTINCT funds, not rows. Share classes of one fund count once. */
  fundCount: number;
  /** Rows, which is what a comparison table actually renders. */
  rowCount: number;
  /**
   * Ranking needs three DISTINCT funds.
   *
   * Counting rows made "Cedi fixed income funds: 4 (rankable)" out of Stanbic
   * Income Fund's two share classes plus two FAAM funds — three funds dressed
   * as four rows. Ranking a fund against its own other share class is not a
   * comparison, and a peer group that is really one fund with three classes
   * would have looked like a comparable set.
   */
  rankable: boolean;
}

const PEER_LABELS: Record<string, string> = {
  "money_market:GHS": "Cedi money market funds",
  "fixed_income:GHS": "Cedi fixed income funds",
  "balanced:GHS": "Cedi balanced funds",
  "equity:GHS": "Listed shares",
  "deposit:GHS": "Cedi fixed deposits and savings accounts",
  "government_security:GHS": "Government Treasury bills",
  "commodity:GHS": "Gold",
};

export const MIN_DISTINCT_FUNDS_TO_RANK = 3;

export async function getPeerGroups(): Promise<PeerGroupSummary[]> {
  const rows = await getPublishedFunds();
  const distinct = new Map<string, Set<string>>();
  const total = new Map<string, number>();
  for (const f of rows) {
    if (!f.peerGroup) continue;
    // Identity is provider + fund name. Share classes collapse to one fund.
    const fundKey = `${f.provider.slug}::${f.name}`;
    if (!distinct.has(f.peerGroup)) distinct.set(f.peerGroup, new Set());
    distinct.get(f.peerGroup)!.add(fundKey);
    total.set(f.peerGroup, (total.get(f.peerGroup) ?? 0) + 1);
  }
  return [...distinct.entries()]
    .map(([peerGroup, funds]) => ({
      peerGroup,
      label: PEER_LABELS[peerGroup] ?? peerGroup,
      fundCount: funds.size,
      rowCount: total.get(peerGroup) ?? 0,
      rankable: funds.size >= MIN_DISTINCT_FUNDS_TO_RANK,
    }))
    .sort((a, b) => b.fundCount - a.fundCount || a.label.localeCompare(b.label));
}

// ---------------------------------------------------------------------------
// Providers
//
// A provider page is what a fund manager is sent a link to, so it has to be
// accurate about what they disclose and what they don't. The disclosure score
// below is built ONLY from what a provider actually publishes — never from a
// judgement about the provider — because the page exists to prompt a
// correction, not to grade anyone.
// ---------------------------------------------------------------------------

export interface ProviderSummary {
  slug: string;
  name: string;
  legalName: string;
  website: string | null;
  custodian: string | null;
  funds: FundRow[];
  /** Documents held for this provider's funds. */
  documentCount: number;
  /** Price points held across all their funds. */
  observationCount: number;
  /** Whether they appear to have stopped publishing — a separate question. */
  publication: PublicationStatus;
  /** Of the fields a comparison needs, how many are filled. 0-1. */
  disclosureScore: number;
  disclosed: { field: string; has: boolean }[];
  /** Most recent price date across all their funds. */
  lastPublished: string | null;
}

const DISCLOSURE_FIELDS: {
  field: string;
  test: (f: FundRow) => boolean;
}[] = [
  { field: "Management fee", test: (f) => f.currentManagementFeePct !== null },
  { field: "Custody fee", test: (f) => f.currentCustodyFeePct !== null },
  {
    field: "Total expense ratio",
    // A part-year figure counts: the provider DOES publish the field, it just
    // has not completed a year. The checklist asks what they disclose.
    test: (f) => f.lastFullYearTerPct !== null || f.partYearTerPct !== null,
  },
  { field: "Minimum investment", test: (f) => f.minimumGhs !== null },
  { field: "Dealing frequency", test: (f) => f.dealingFrequency !== null },
  { field: "Unit price", test: (f) => f.latestNav !== null },
  { field: "12+ months of history", test: (f) => f.observationCount >= 12 },
];

// Deliberately NOT a disclosure field: whether prices are recent.
//
// "Prices within 90 days" sat in the checklist beside "Total expense ratio" as
// though both were things a provider had failed to publish. They are different
// failures. A missing expense ratio means the factsheet does not carry the
// field. A stale price means the factsheets stopped — FAAM's most recent is
// February 2026 and they publish monthly, so something changed rather than
// something is absent.
//
// Asking a manager to "publish prices within 90 days" when they publish
// monthly reads as though we have not looked. Asking "your latest factsheet we
// hold is February — have you published since?" is a question they can answer,
// and the answer may be that they moved somewhere we cannot see.
export interface PublicationStatus {
  latestDocument: string | null;
  monthsSince: number | null;
  looksPaused: boolean;
}

export async function getProviders(): Promise<ProviderSummary[]> {
  const funds = await getPublishedFunds();
  const { data, error } = await publicClient()
    .from("providers")
    .select("slug, trading_name, legal_name, website, custodian, status")
    .eq("status", "published");
  if (error) throw new Error(`getProviders: ${error.message}`);

  return (data ?? [])
    .map((p: Record<string, unknown>) => {
      const slug = String(p.slug);
      const mine = funds.filter((f) => f.provider.slug === slug);
      const disclosed = DISCLOSURE_FIELDS.map(({ field, test }) => ({
        field,
        // A provider discloses a field if ANY of their funds does — the page
        // asks "do you publish this at all", not "do you publish it everywhere".
        has: mine.some(test),
      }));
      const dates = mine
        .map((f) => f.lastObservation)
        .filter((d): d is string => Boolean(d))
        .sort();
      // Every document behind every figure we hold for them — not just the
      // handful cited by whatever is currently on screen. "Documents held: 2"
      // when 34 of their factsheets are on disk reads, from their side, as
      // though we barely know them.
      const docs = new Set(
        mine.flatMap((f) => [
          f.statedChargesPct?.source,
          f.currentManagementFeePct?.source,
          f.currentCustodyFeePct?.source,
          f.lastFullYearTerPct?.source,
          f.latestNav?.source,
          f.minimumGhs?.source,
          ...f.feeHistory.map((h) => h.source),
        ]),
      );
      docs.delete(undefined);
      docs.delete("unverified");
      const observations = mine.reduce((a, f) => a + f.observationCount, 0);
      return {
        slug,
        name: String(p.trading_name ?? p.legal_name ?? slug),
        legalName: String(p.legal_name ?? ""),
        website: (p.website as string | null) ?? null,
        custodian: (p.custodian as string | null) ?? null,
        funds: mine,
        documentCount: docs.size,
        observationCount: observations,
        publication: {
          latestDocument: dates[dates.length - 1] ?? null,
          monthsSince: dates.length
            ? Math.round(
                (Date.now() -
                  new Date(dates[dates.length - 1] + "T00:00:00Z").getTime()) /
                  (30 * 86_400_000),
              )
            : null,
          // Monthly publishers who have gone quiet for a quarter have paused,
          // not failed to disclose.
          looksPaused: dates.length
            ? Date.now() -
                new Date(dates[dates.length - 1] + "T00:00:00Z").getTime() >
              100 * 86_400_000
            : false,
        },
        disclosureScore:
          disclosed.filter((d) => d.has).length / DISCLOSURE_FIELDS.length,
        disclosed,
        lastPublished: dates[dates.length - 1] ?? null,
      };
    })
    .filter((p) => p.funds.length > 0)
    .sort((a, b) => b.disclosureScore - a.disclosureScore);
}

export async function getProvider(slug: string): Promise<ProviderSummary | null> {
  const all = await getProviders();
  return all.find((p) => p.slug === slug) ?? null;
}

// ---------------------------------------------------------------------------
// The yield bridge (§7.1) — what the investor actually keeps
// ---------------------------------------------------------------------------

export interface BridgeStep {
  label: string;
  /** Null means the figure is genuinely unavailable, not zero. */
  valuePct: number | null;
  kind: "gross" | "deduction" | "subtotal" | "headline" | "unavailable";
  note?: string;
}

/**
 * Build the bridge from gross return down to what is kept.
 *
 * The tax step is UNAVAILABLE, not omitted. Ghanaian withholding on investment
 * income has not been verified with an accountant and products.withholding_rate
 * is null everywhere, so silently skipping it would overstate the result. An
 * absent step that says it is absent is honest; a missing step is not.
 */
export function buildYieldBridge(
  grossAnnualisedPct: number | null,
  fund: FundRow,
  inflationPct: number | null,
): BridgeStep[] {
  const steps: BridgeStep[] = [];
  if (grossAnnualisedPct === null) {
    return [
      {
        label: "Return",
        valuePct: null,
        kind: "unavailable",
        note: "Not enough verified price history to calculate a return.",
      },
    ];
  }

  steps.push({ label: "Return before costs", valuePct: grossAnnualisedPct, kind: "gross" });

  // Published fund returns are normally already net of fees. Showing the fee
  // as a further deduction would double-count it, so it is listed for context
  // and not subtracted.
  const mgmt = fund.currentManagementFeePct?.value ?? null;
  const cust = fund.currentCustodyFeePct?.value ?? null;
  if (mgmt !== null || cust !== null) {
    steps.push({
      label: "Annual charges",
      valuePct: (mgmt ?? 0) + (cust ?? 0),
      kind: "deduction",
      note: "Already reflected in the published return — shown for comparison.",
    });
  }

  steps.push({
    label: "Withholding tax",
    valuePct: null,
    kind: "unavailable",
    note: "Ghanaian withholding treatment not yet verified — this figure is missing, not zero.",
  });

  if (inflationPct !== null) {
    steps.push({ label: "Inflation", valuePct: -inflationPct, kind: "deduction" });
    // Fisher, not subtraction: at Ghanaian inflation levels the approximation
    // is materially wrong.
    const real = ((1 + grossAnnualisedPct / 100) / (1 + inflationPct / 100) - 1) * 100;
    steps.push({
      label: "What you keep, before tax",
      valuePct: Number(real.toFixed(2)),
      kind: "headline",
    });
  }
  return steps;
}

/**
 * getTicker — the live numbers for the bar across the top of the home page.
 *
 * Five figures, each from a document its issuer published, and no other
 * Ghanaian site carries them together. A visitor seeing them learns what this
 * site is in two seconds without reading a word.
 *
 * EVERY ITEM CARRIES ITS DATE. A ticker implies "now", and most of these are
 * not: the GSE index is from a monthly report that may be six weeks old, the
 * Treasury bill rate from the last tender. Presenting a July figure as today's
 * would be exactly the unstated staleness this site criticises elsewhere.
 */
export interface TickerItem {
  label: string;
  value: string;
  direction?: "up" | "down";
  asOf?: string;
  /** Recent observations, oldest first, for the inline sparkline. */
  series?: number[];
}

export async function getTicker(): Promise<TickerItem[]> {
  const out: TickerItem[] = [];
  const shortDate = (iso: string) =>
    new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      timeZone: "UTC",
    });

  try {
    // Treasury bills: the two tenors a saver actually meets.
    const { data: bills } = await publicClient()
      .from("products")
      .select("name, nav_observations ( as_of, yield_annualised )")
      .eq("asset_class", "government_security")
      .eq("status", "published");

    for (const want of ["91", "364"]) {
      const p = (bills ?? []).find((b: Record<string, unknown>) =>
        String(b.name).includes(want),
      );
      if (!p) continue;
      const obs = [
        ...((p.nav_observations ?? []) as {
          as_of: string;
          yield_annualised: number | null;
        }[]),
      ]
        .filter((o) => o.yield_annualised !== null)
        .sort((a, b) => a.as_of.localeCompare(b.as_of));
      if (!obs.length) continue;
      const last = obs[obs.length - 1];
      const prev = obs[obs.length - 2];
      out.push({
        label: `${want}-day bill`,
        value: `${(last.yield_annualised! * 100).toFixed(2)}%`,
        direction: prev
          ? last.yield_annualised! >= prev.yield_annualised!
            ? "up"
            : "down"
          : undefined,
        asOf: shortDate(last.as_of),
        series: obs.slice(-14).map((o) => o.yield_annualised! * 100),
      });
    }
  } catch {
    // A ticker is not worth failing a page load over.
  }

  try {
    const { data: idx } = await publicClient()
      .from("macro_series")
      .select("as_of, value")
      .eq("series_code", "GSE_COMPOSITE_INDEX")
      .order("as_of", { ascending: false })
      .limit(15);
    if (idx?.length) {
      out.push({
        label: "GSE index",
        value: Number(idx[0].value).toLocaleString("en-GB", {
          maximumFractionDigits: 0,
        }),
        direction:
          idx[1] && Number(idx[0].value) >= Number(idx[1].value) ? "up" : "down",
        asOf: shortDate(String(idx[0].as_of)),
        series: [...idx].reverse().map((r) => Number(r.value)),
      });
    }
  } catch {
    /* as above */
  }

  try {
    const { data: gold } = await publicClient()
      .from("products")
      .select("nav_observations ( as_of, nav )")
      .eq("slug", "ghana-gold-coin-1-00oz")
      .single();
    const obs = [
      ...(((gold as Record<string, unknown>)?.nav_observations ?? []) as {
        as_of: string;
        nav: number | null;
      }[]),
    ]
      .filter((o) => o.nav !== null)
      .sort((a, b) => a.as_of.localeCompare(b.as_of));
    if (obs.length) {
      const last = obs[obs.length - 1];
      const prev = obs[obs.length - 2];
      out.push({
        label: "Gold coin, 1oz",
        value: `GH\u20B5${Math.round(last.nav!).toLocaleString("en-GB")}`,
        direction: prev ? (last.nav! >= prev.nav! ? "up" : "down") : undefined,
        asOf: shortDate(last.as_of),
        series: obs.slice(-20).map((o) => o.nav!),
      });
    }
  } catch {
    /* as above */
  }

  try {
    // Four listed shares, chosen by SIZE rather than performance.
    //
    // Whatever sits in a ticker gets seen, so the choice is editorial. Ranking
    // by return would put Clydestone first at +15,733% — true, and thoroughly
    // misleading for a share that started at three pesewas. Market
    // capitalisation is neutral: nobody can call the biggest companies a
    // cherry-pick, and it is the same rule an index uses.
    const { data: shares } = await publicClient()
      .from("products")
      .select("name, nav_observations ( as_of, nav )")
      .eq("asset_class", "equity")
      .eq("status", "published");

    const sized = (shares ?? [])
      .map((s: Record<string, unknown>) => {
        const obs = [
          ...((s.nav_observations ?? []) as { as_of: string; nav: number | null }[]),
        ]
          .filter((o) => o.nav !== null)
          .sort((a, b) => a.as_of.localeCompare(b.as_of));
        const ticker = String(s.name).split("\u00B7")[0].trim();
        return { ticker, obs };
      })
      .filter((s) => s.obs.length >= 3);

    // Market cap is not stored per product, so the largest four by PRICE
    // stand in. Not the same thing — a high price does not mean a big
    // company — but it is at least not a performance ranking, and the
    // alternative is showing none.
    sized.sort(
      (a, b) =>
        (b.obs[b.obs.length - 1].nav ?? 0) - (a.obs[a.obs.length - 1].nav ?? 0),
    );

    for (const s of sized.slice(0, 4)) {
      const last = s.obs[s.obs.length - 1];
      const prev = s.obs[s.obs.length - 2];
      out.push({
        label: s.ticker,
        value: `GH\u20B5${last.nav!.toFixed(2)}`,
        direction: prev ? (last.nav! >= prev.nav! ? "up" : "down") : undefined,
        asOf: shortDate(last.as_of),
        series: s.obs.slice(-15).map((o) => o.nav!),
      });
    }
  } catch {
    /* a ticker is not worth failing a page load over */
  }

  return out;
}
