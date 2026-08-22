/**
 * app/compare/[group]/page.tsx — what these funds cost.
 *
 * DESIGN DIRECTION
 * Structure and energy from Serrari — gradient hero holding the headline
 * number, pill tabs, ranked cards, rounded white cards on a tinted background,
 * serif display against a rounded sans. Palette deliberately NOT their
 * purple-magenta: copying it into an adjacent African market reads as
 * derivative. Teal to gold instead — gold has a genuine Ghanaian claim (the
 * Gold Coast, the cedi, kente) without being a flag pastiche.
 *
 * Two typefaces. Fraunces carries the personality, Plus Jakarta Sans does the
 * work and supplies tabular figures, so no separate mono. The audience is on
 * Ghanaian mobile data and §7.3 sets a 100KB budget.
 *
 * FOUR FIXES IN v3, all found by looking at the rendered page:
 *
 *  1. FRESHNESS WORDING was inconsistent — "Since 1 Feb 2026" on one card and
 *     "52 days old" on another. The first reads like a start date rather than
 *     a warning that the data is seven months stale. Now always an age.
 *
 *  2. SHARE CLASSES rendered as separate cards that looked like duplicates:
 *     same fund name, same 2.25%, same minimum, differing only in a small
 *     SIFT / SIFTAMC label. On a costs-only page the classes ARE identical, so
 *     they collapse into one card that names them. They will need separating
 *     when returns land — Cash Trust's classes returned 36.88% and 14.04% over
 *     the same year — but showing what looks like a duplicate row today costs
 *     more trust than it buys.
 *
 *  3. BAR SCALING started at zero, so a 0.50pp spread looked like near-parity:
 *     2.10% drew almost as long as 2.25%. Now scaled across the group's actual
 *     range so the bar encodes the difference a reader cares about.
 *
 *  4. SOURCE COUNT said 5 when the corpus is 86 — it counted documents cited
 *     by visible figures, not documents held.
 */

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";
import { notFound } from "next/navigation";

import { BRAND } from "@/lib/brand";
import {
  MIN_DISTINCT_FUNDS_TO_RANK,
  getFundsByPeerGroup,
  getPeerGroups,
  getPublishedFunds,
  type FundRow,
  type Sourced,
} from "@/lib/data/funds";

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
  ink: "#0C1F1C",
  deep: "#0A5D52",
  teal: "#128B7A",
  gold: "#E8A33D",
  clay: "#C0492B",
  bg: "#F3F6F3",
  card: "#FFFFFF",
  rule: "#DCE5E0",
  muted: "#5F726C",
  good: "#0E8F62",
};

const GHS = new Intl.NumberFormat("en-GH", {
  style: "currency",
  currency: "GHS",
  maximumFractionDigits: 0,
});

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** Always an age, never a start date. "Since 1 Feb" reads as a beginning. */
function ageLabel(days: number | null): string {
  if (days === null) return "No date";
  if (days < 45) return `${days} days old`;
  const months = Math.round(days / 30);
  if (months < 18) return `${months} months old`;
  return `${(days / 365).toFixed(1)} years old`;
}

/** No figure without its receipt. Permanently visible, not a hover reveal. */
function Receipt({ from }: { from: Sourced<unknown> | null }) {
  if (!from) return null;
  return (
    <p
      className="mt-1.5 truncate text-[10px] tracking-wide"
      style={{ color: C.muted }}
      title={`${from.source} · verified ${from.asOf}`}
    >
      <span style={{ color: C.teal }}>✓</span> Charges confirmed{" "}
      {fmtDate(from.asOf)}
      {from.sourceHash && <span className="opacity-60"> · {from.sourceHash}</span>}
    </p>
  );
}

/** One card per FUND. Share classes are listed inside it. */
interface FundGroup {
  key: string;
  primary: FundRow;
  classes: FundRow[];
}

function groupByFund(rows: FundRow[]): FundGroup[] {
  const map = new Map<string, FundRow[]>();
  for (const r of rows) {
    const k = `${r.provider.slug}::${r.name}`;
    if (!map.has(k)) map.set(k, []);
    map.get(k)!.push(r);
  }
  return [...map.entries()].map(([key, classes]) => ({
    key,
    primary: classes.find((c) => c.shareClass === "main") ?? classes[0],
    classes: classes.sort((a, b) => a.shareClass.localeCompare(b.shareClass)),
  }));
}

export async function generateStaticParams() {
  const groups = await getPeerGroups();
  return groups.map((g) => ({ group: g.peerGroup.replace(":", "-") }));
}

export const revalidate = 3600;

export default async function ComparePage({
  params,
}: {
  params: Promise<{ group: string }>;
}) {
  const { group } = await params;
  const peerGroup = group.replace("-", ":");
  const [groups, all] = await Promise.all([getPeerGroups(), getPublishedFunds()]);
  const summary = groups.find((g) => g.peerGroup === peerGroup);
  if (!summary) notFound();

  const rows = await getFundsByPeerGroup(peerGroup);
  if (rows.length === 0) notFound();

  // Cheapest first. No published charge sorts LAST — absent is not free.
  const funds = groupByFund(rows).sort((a, b) => {
    const av = a.primary.statedChargesPct?.value ?? Number.POSITIVE_INFINITY;
    const bv = b.primary.statedChargesPct?.value ?? Number.POSITIVE_INFINITY;
    return av - bv || a.primary.name.localeCompare(b.primary.name);
  });

  const charges = funds
    .map((f) => f.primary.statedChargesPct?.value)
    .filter((v): v is number => typeof v === "number");
  const cheapest = charges.length ? Math.min(...charges) : null;
  const dearest = charges.length ? Math.max(...charges) : null;
  const average = charges.length
    ? charges.reduce((a, b) => a + b, 0) / charges.length
    : null;

  // Every document behind every published figure, across the whole database —
  // not just the ones cited on this page.
  const corpus = new Set(
    all.flatMap((f) => [
      f.statedChargesPct?.source,
      f.currentManagementFeePct?.source,
      f.currentCustodyFeePct?.source,
      f.lastFullYearTerPct?.source,
      f.latestNav?.source,
      f.minimumGhs?.source,
      ...f.feeHistory.map((h) => h.source),
    ]),
  );
  corpus.delete(undefined);
  corpus.delete("unverified");

  /**
   * Bars scale across the group's RANGE, not from zero. From zero, a 0.50pp
   * spread renders as near-parity — 2.10% drew almost as long as 2.25% — which
   * hides the only thing the bar is there to show.
   */
  function barWidth(v: number): number {
    if (cheapest === null || dearest === null || dearest === cheapest) return 100;
    return 16 + ((v - cheapest) / (dearest - cheapest)) * 84;
  }

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div
        className="w-full px-5 py-2 text-center text-[11px] font-medium tracking-wide text-white"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        {all.length} funds tracked · {corpus.size} source documents · every figure
        dated
      </div>

      <header className="mx-auto max-w-4xl px-5 pt-6 sm:px-8">
        <Link
          href="/"
          className="text-[19px] font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: C.deep }}
        >
          {BRAND.name}
        </Link>
      </header>

      <div className="mx-auto max-w-4xl px-5 py-8 sm:px-8 sm:py-10">
        <section
          className="overflow-hidden rounded-3xl p-7 text-white sm:p-10"
          style={{
            background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 62%, ${C.gold} 190%)`,
          }}
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-80">
            {summary.label}
          </p>
          <h1
            className="mt-3 text-[2.1rem] font-bold leading-[1.08] sm:text-[3rem]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            What these funds
            <br />
            actually cost
          </h1>

          {cheapest !== null && (
            <div className="mt-8 grid grid-cols-3 gap-4 sm:max-w-lg">
              {[
                { k: "Cheapest", v: cheapest, hi: true },
                { k: "Average", v: average! },
                { k: "Priciest", v: dearest! },
              ].map(({ k, v, hi }) => (
                <div key={k}>
                  <p className="text-[10px] uppercase tracking-wider opacity-75">{k}</p>
                  <p
                    className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]"
                    style={{ color: hi ? C.gold : "#fff" }}
                  >
                    {v.toFixed(2)}%
                  </p>
                </div>
              ))}
            </div>
          )}

          <p className="mt-7 max-w-xl text-[14px] leading-relaxed opacity-90">
            Compared on the charges every provider publishes — annual management
            fee plus custody. Not every fund discloses a total expense ratio, so
            this is the figure that compares like with like.
          </p>
        </section>

        <nav className="mt-7 flex flex-wrap gap-2">
          {groups.map((g) => {
            const active = g.peerGroup === peerGroup;
            return (
              <Link
                key={g.peerGroup}
                href={`/compare/${g.peerGroup.replace(":", "-")}`}
                className="rounded-full px-4 py-2 text-[13px] font-semibold transition-colors"
                style={{
                  background: active ? C.deep : C.card,
                  color: active ? "#fff" : C.ink,
                  border: `1px solid ${active ? C.deep : C.rule}`,
                }}
              >
                {g.label}
                <span className="ml-1.5 opacity-60">{g.fundCount}</span>
              </Link>
            );
          })}
        </nav>

        {!summary.rankable && (
          <p
            className="mt-6 rounded-2xl px-5 py-4 text-[13px] leading-relaxed"
            style={{ background: `${C.gold}1A`, color: C.ink }}
          >
            <strong>Listed cheapest first, not ranked.</strong> Ranking needs at
            least {MIN_DISTINCT_FUNDS_TO_RANK} separate funds and this group has{" "}
            {summary.fundCount}. A cheaper fund is not automatically the right
            one for your goal.
          </p>
        )}

        <ol className="mt-6 space-y-4">
          {funds.map((fg, i) => {
            const fund = fg.primary;
            const charge = fund.statedChargesPct;
            const isCheapest =
              charge && cheapest !== null && charge.value === cheapest;
            const multiClass = fg.classes.length > 1;
            return (
              <li
                key={fg.key}
                className="rounded-3xl p-6 sm:p-7"
                style={{
                  background: C.card,
                  border: `1px solid ${isCheapest ? C.gold : C.rule}`,
                  boxShadow: isCheapest
                    ? `0 1px 3px ${C.gold}33`
                    : "0 1px 2px rgba(12,31,28,0.04)",
                }}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span
                      className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[12px] font-bold"
                      style={{
                        background: isCheapest ? C.gold : `${C.teal}1A`,
                        color: isCheapest ? C.ink : C.deep,
                      }}
                    >
                      {i + 1}
                    </span>
                    <div className="min-w-0">
                      <h2
                        className="text-[17px] font-bold leading-snug"
                        style={{ fontFamily: "var(--font-display)" }}
                      >
                        {fund.name}
                      </h2>
                      <p className="mt-0.5 text-[13px]" style={{ color: C.muted }}>
                        {fund.provider.name}
                      </p>
                    </div>
                  </div>
                  <span
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium"
                    style={{
                      color: fund.staleness === "current" ? C.good : C.clay,
                      background:
                        fund.staleness === "current"
                          ? `${C.good}14`
                          : `${C.clay}14`,
                    }}
                  >
                    <span
                      aria-hidden
                      className="h-1.5 w-1.5 rounded-full"
                      style={{
                        background:
                          fund.staleness === "current" ? C.good : C.clay,
                      }}
                    />
                    {fund.staleness === "current"
                      ? "Prices up to date"
                      : `Prices ${ageLabel(fund.daysSinceLastObservation)}`}
                  </span>
                </div>

                <div className="mt-6">
                  {charge ? (
                    <>
                      <div className="flex items-baseline gap-2">
                        <span
                          className="text-[2.4rem] font-bold tabular-nums leading-none"
                          style={{ color: isCheapest ? C.deep : C.ink }}
                        >
                          {charge.value.toFixed(2)}%
                        </span>
                        <span className="text-[13px]" style={{ color: C.muted }}>
                          a year
                        </span>
                        {isCheapest && (
                          <span
                            className="ml-auto rounded-full px-3 py-1 text-[11px] font-bold"
                            style={{ background: C.gold, color: C.ink }}
                          >
                            Lowest here
                          </span>
                        )}
                      </div>
                      <div
                        className="mt-3.5 h-2 w-full overflow-hidden rounded-full"
                        style={{ background: C.rule }}
                      >
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${barWidth(charge.value)}%`,
                            background: isCheapest
                              ? `linear-gradient(90deg, ${C.deep}, ${C.gold})`
                              : C.teal,
                          }}
                        />
                      </div>
                      <Receipt from={charge} />
                    </>
                  ) : (
                    <p className="text-[15px] font-medium" style={{ color: C.clay }}>
                      Charges not published
                    </p>
                  )}
                </div>

                <dl
                  className="mt-6 grid grid-cols-2 gap-x-5 gap-y-4 border-t pt-5 text-[13px] sm:grid-cols-4"
                  style={{ borderColor: C.rule }}
                >
                  {[
                    {
                      t: "Minimum",
                      v: fund.minimumGhs ? GHS.format(fund.minimumGhs.value) : "—",
                    },
                    {
                      t: "Management",
                      v: fund.currentManagementFeePct
                        ? `${fund.currentManagementFeePct.value.toFixed(2)}%`
                        : "—",
                    },
                    {
                      t: "Custody",
                      v: fund.currentCustodyFeePct
                        ? `${fund.currentCustodyFeePct.value.toFixed(2)}%`
                        : "—",
                    },
                    {
                      t: "Dealing",
                      v: fund.dealingFrequency
                        ? fund.dealingFrequency.charAt(0).toUpperCase() +
                          fund.dealingFrequency.slice(1)
                        : "—",
                    },
                  ].map(({ t, v }) => (
                    <div key={t}>
                      <dt
                        className="text-[11px] uppercase tracking-wider"
                        style={{ color: C.muted }}
                      >
                        {t}
                      </dt>
                      <dd className="mt-1 font-semibold tabular-nums">{v}</dd>
                    </div>
                  ))}
                </dl>

                {multiClass && (
                  <p
                    className="mt-4 rounded-xl px-4 py-3 text-[12.5px] leading-relaxed"
                    style={{ background: `${C.teal}0F`, color: C.ink }}
                  >
                    <strong>
                      {fg.classes.length} share classes — same charges, different
                      returns.
                    </strong>{" "}
                    {fg.classes
                      .map((c) => c.shareClassLabel ?? c.shareClass)
                      .join(" and ")}
                    . They hold different assets, so their performance differs
                    even though the fees do not.
                  </p>
                )}

                {fund.feeChanged &&
                  (() => {
                    const h = fund.feeHistory
                      .filter((x) => x.feeType === "stated_charges")
                      .sort((a, b) =>
                        a.effectiveFrom.localeCompare(b.effectiveFrom),
                      );
                    const was = h[0];
                    const now = h[h.length - 1];
                    if (!was || !now || was === now) return null;
                    return (
                      <p
                        className="mt-4 rounded-xl px-4 py-3 text-[12.5px] font-medium"
                        style={{ background: `${C.good}12`, color: C.good }}
                      >
                        Charges cut from {was.ratePct.toFixed(2)}% to{" "}
                        {now.ratePct.toFixed(2)}% on {fmtDate(now.effectiveFrom)}
                      </p>
                    );
                  })()}

                {fund.distributes && (
                  <p className="mt-3 text-[12px]" style={{ color: C.muted }}>
                    Pays income out, so the unit price drops on a distribution. A
                    fall is not necessarily a loss.
                  </p>
                )}
              </li>
            );
          })}
        </ol>

        <section
          className="mt-10 rounded-3xl p-6 sm:p-8"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2
            className="text-[18px] font-bold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            What this page doesn&rsquo;t show
          </h2>
          <ul
            className="mt-4 space-y-3 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            <li>
              <strong style={{ color: C.ink }}>Tax.</strong> Ghanaian withholding
              on investment income hasn&rsquo;t been verified, so it&rsquo;s
              missing here rather than assumed to be nil. You&rsquo;ll keep less
              than these charges alone suggest.
            </li>
            <li>
              <strong style={{ color: C.ink }}>Past returns.</strong> Each
              provider publishes them. They don&rsquo;t predict what a fund does
              next, and they&rsquo;re not shown here yet.
            </li>
            <li>
              <strong style={{ color: C.ink }}>Fee history</strong> starts when
              our records start, not when the fee did.
            </li>
          </ul>
          <p className="mt-6 text-[11px] leading-relaxed" style={{ color: C.muted }}>
            {BRAND.legalStatus}
          </p>
        </section>
      </div>
    </main>
  );
}
