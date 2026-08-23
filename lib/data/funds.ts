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

  currentManagementFeePct: Sourced<number> | null;
  currentCustodyFeePct: Sourced<number> | null;
  /**
   * Management plus custody, as disclosed. THE cross-provider cost figure:
   * FAAM publishes no expense ratio at all, so comparing Stanbic's TER against
   * FAAM's stated charges would compare two different things.
   */
  statedChargesPct: Sourced<number> | null;
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
  min_initial_minor: number | null;
  min_verified_on: string | null;
  providers: { trading_name: string | null; legal_name: string; slug: string } | null;
  product_fees: RawFee[];
  nav_observations: RawObs[];
  product_metrics: RawMetric[];
}

const SELECT = `
  id, slug, name, share_class, share_class_label, asset_class, peer_group,
  currency, distributes, dealing_frequency, min_initial_minor, min_verified_on,
  providers ( trading_name, legal_name, slug ),
  product_fees ( fee_type, rate, effective_from, effective_to, verified_on,
                 conditions, sources ( title, content_sha256 ) ),
  nav_observations ( as_of, nav, series_kind, sources ( title, content_sha256 ) ),
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

  const mgmt = currentFee(p.product_fees ?? [], "management");
  const cust = currentFee(p.product_fees ?? [], "custody");
  const ter = lastFullYearTer(p.product_fees ?? []);
  const stated = currentFee(p.product_fees ?? [], "stated_charges");
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
    statedChargesPct: stated
      ? sourced(
          Number((stated.rate * 100).toFixed(4)),
          stated.verified_on ?? stated.effective_from,
          stated.sources,
        )
      : null,
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

export async function getPublishedFunds(): Promise<FundRow[]> {
  const { data, error } = await publicClient()
    .from("products")
    .select(SELECT)
    .eq("status", "published")
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
  "equity:GHS": "Cedi equity funds",
  "deposit:GHS": "Cedi fixed deposits and savings accounts",
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
