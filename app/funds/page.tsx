/**
 * app/funds/page.tsx — every Ghanaian fund we know exists.
 *
 * TWO AUDIENCES, OPPOSITE NEEDS.
 *
 * An investor wants the five funds with verified figures. A fund manager wants
 * to find their own, see the blanks, and be given a reason to fill them — the
 * outreach email says "your fund is listed and three fields are blank", which
 * is a correction request rather than a favour, and that only works if the
 * blanks are visible and honest.
 *
 * v2 FIXES THE HIERARCHY. v1 gave the five COVERED funds a flat list and
 * grouped the 67 uncovered ones by category — the wrong way round. The funds
 * with real data now get grouped, carded and detailed; the directory entries
 * are condensed to a dense scan, because a name with no figures needs a line,
 * not a card.
 */

import Link from "next/link";

import Footer from "@/components/Footer";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import { BRAND } from "@/lib/brand";
import {
  getDirectory,
  getPeerGroups,
  getPublishedFunds,
  type FundRow,
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

const CLASS_LABEL: Record<string, string> = {
  money_market: "Money market",
  fixed_income: "Fixed income",
  balanced: "Balanced",
  equity: "Equity",
  real_estate: "Real estate",
  deposit: "Deposits",
  uncategorised: "Category not established",
};

const GHS = new Intl.NumberFormat("en-GH", {
  style: "currency",
  currency: "GHS",
  maximumFractionDigits: 0,
});

const toUrl = (peerGroup: string) => peerGroup.replace(/:([^:]*)$/, "-$1");

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export const metadata = {
  title: "Ghanaian mutual fund charges compared — 75 funds",
  description:
    "What Ghanaian mutual funds charge, from their own factsheets. Management fees, total expense ratios and minimum investments for every fund we can verify.",
};
export const revalidate = 3600;

export default async function FundsPage() {
  const [covered, directory, groups] = await Promise.all([
    getPublishedFunds(),
    getDirectory(),
    getPeerGroups(),
  ]);

  // One entry per fund, not per share class.
  const coveredFunds = [
    ...new Map(covered.map((f) => [`${f.provider.slug}::${f.name}`, f])).values(),
  ];

  const coveredByClass = new Map<string, FundRow[]>();
  for (const f of coveredFunds) {
    const k = f.assetClass ?? "uncategorised";
    if (!coveredByClass.has(k)) coveredByClass.set(k, []);
    coveredByClass.get(k)!.push(f);
  }
  for (const list of coveredByClass.values()) {
    list.sort(
      (a, b) =>
        (a.statedChargesPct?.value ?? 99) - (b.statedChargesPct?.value ?? 99),
    );
  }

  const dirByClass = new Map<string, typeof directory>();
  for (const d of directory) {
    const k = d.assetClass ?? "uncategorised";
    if (!dirByClass.has(k)) dirByClass.set(k, []);
    dirByClass.get(k)!.push(d);
  }

  const total = coveredFunds.length + directory.length;

  // The lowest minimum any verified fund actually accepts. Quoted in the
  // audience section below, so it must come from the data rather than be
  // typed in — a hardcoded "GH¢20" would go stale the day a cheaper fund is
  // verified, and stale specifics are exactly what this site tells providers
  // off for.
  const minimums = coveredFunds
    .map((f) => f.minimumGhs?.value)
    .filter((v): v is number => typeof v === "number");
  const cheapestMin = minimums.length
    ? GHS.format(Math.min(...minimums))
    : "small";

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div
        className="w-full px-5 py-2 text-center text-[11px] font-medium tracking-wide text-white"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        {total} Ghanaian funds tracked · {coveredFunds.length} with verified
        charges
      </div>

      <div className="mx-auto max-w-4xl px-5 py-8 sm:px-8 sm:py-10">
        <section
          className="overflow-hidden rounded-3xl p-7 text-white sm:p-10"
          style={{
            background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 62%, ${C.gold} 190%)`,
          }}
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-80">
            The Ghanaian fund universe
          </p>
          <h1
            className="mt-3 text-[2.1rem] font-bold leading-[1.08] sm:text-[3rem]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Every fund
            <br />
            we know of
          </h1>
          <div className="mt-8 grid grid-cols-3 gap-4 sm:max-w-md">
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Tracked
              </p>
              <p className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]">
                {total}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Verified
              </p>
              <p
                className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]"
                style={{ color: C.gold }}
              >
                {coveredFunds.length}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Awaiting data
              </p>
              <p className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]">
                {directory.length}
              </p>
            </div>
          </div>
          <p className="mt-7 max-w-xl text-[14px] leading-relaxed opacity-90">
            A directory that hides its gaps isn&rsquo;t worth trusting. Where we
            have a provider&rsquo;s own documents we show the figures and the
            dates. Where we don&rsquo;t, we say so.
          </p>
        </section>

        {/* COVERED — grouped, carded, detailed */}
        {/*
          Restored here rather than on the home page. It was written for the
          investing side — Ghana Card routes, fund eligibility, who a provider
          will accept as a subscriber — and none of that carries over to the
          borrowing side, where a business needs registration and presence in
          Ghana. Putting it on a page that serves both audiences would make it
          wrong for half of them.

          The honesty is the point: two of the three cards say what is still
          unestablished. A diaspora Ghanaian who reads "we don't yet know which
          funds accept you" has learned something true, which is better than a
          confident answer we cannot support.
        */}
        <h2
          className="mt-14 text-[24px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Who this is for
        </h2>
        <p className="mt-2 max-w-2xl text-[13.5px]" style={{ color: C.muted }}>
          The funds here are regulated in Ghana. Who can buy them depends on each
          provider&rsquo;s own rules, and those rules aren&rsquo;t published in
          one place — so here&rsquo;s what we&rsquo;ve established and
          what we&rsquo;re still working out.
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {[
            {
              title: "Living in Ghana",
              state: "Everything here applies",
              tone: C.good,
              detail: `All the figures on this site are for you. The lowest minimum we've found is ${cheapestMin}, and most funds deal daily.`,
              open: null,
            },
            {
              title: "Ghanaian abroad",
              state: "The route exists",
              tone: C.teal,
              detail:
                "The Ghana Card is the key, and it's obtainable from abroad — the NIA runs a digital-first process through Ghana's missions, with biometrics captured at your nearest one.",
              open:
                "Still checking: which funds accept subscribers who live outside Ghana, and how money moves in and out.",
            },
            {
              title: "Investing from outside",
              state: "Least mapped",
              tone: C.clay,
              detail:
                "Non-citizens need a different form of national ID, and fund eligibility rules vary by provider.",
              open:
                "Still checking: which funds are open to non-citizens at all, and what documentation they require.",
            },
          ].map((a) => (
            <div
              key={a.title}
              className="rounded-2xl p-5"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <h3
                className="text-[16px] font-bold"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {a.title}
              </h3>
              <span
                className="mt-2 inline-block rounded-full px-2.5 py-1 text-[10.5px] font-semibold"
                style={{ background: `${a.tone}14`, color: a.tone }}
              >
                {a.state}
              </span>
              <p
                className="mt-3 text-[12.5px] leading-relaxed"
                style={{ color: C.muted }}
              >
                {a.detail}
              </p>
              {a.open && (
                <p
                  className="mt-3 border-t pt-3 text-[12px] leading-relaxed"
                  style={{ borderColor: C.rule, color: C.clay }}
                >
                  {a.open}
                </p>
              )}
            </div>
          ))}
        </div>

        {/*
          Seventy-five funds is a lot to read through, and someone who does not
          already know what they want will bounce off a list this long. The
          narrowing flow is offered here, beside the problem it solves, rather
          than only on a home page they may never come back to.
        */}
        <Link
          href="/match"
          className="mt-10 flex flex-wrap items-center justify-between gap-3 rounded-2xl px-5 py-4"
          style={{ background: `${C.teal}0F`, border: `1px solid ${C.teal}40` }}
        >
          <span className="text-[13.5px]">
            <strong>Too many to read through?</strong> Answer eight questions
            and we&rsquo;ll show only what fits what you told us.
          </span>
          <span
            className="shrink-0 rounded-full px-4 py-2 text-[12.5px] font-bold text-white"
            style={{ background: C.deep }}
          >
            Narrow it down →
          </span>
        </Link>

        <h2
          className="mt-12 text-[24px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Verified funds
        </h2>
        <p className="mt-2 text-[13.5px]" style={{ color: C.muted }}>
          Charges, minimums and access terms taken from each provider&rsquo;s own
          published documents, with the date each figure was confirmed.
        </p>

        <div className="mt-6 space-y-9">
          {[...coveredByClass.entries()]
            .sort((a, b) => b[1].length - a[1].length)
            .map(([cls, funds]) => (
              <section key={cls}>
                <div className="flex items-baseline justify-between gap-3">
                  <h3
                    className="text-[13px] font-bold uppercase tracking-wider"
                    style={{ color: C.deep }}
                  >
                    {CLASS_LABEL[cls] ?? cls}
                    <span className="ml-2 font-normal" style={{ color: C.muted }}>
                      {funds.length}
                    </span>
                  </h3>
                  {funds[0]?.peerGroup && (
                    <Link
                      href={`/compare/${toUrl(funds[0].peerGroup)}`}
                      className="text-[12.5px] font-semibold underline underline-offset-4"
                      style={{ color: C.deep }}
                    >
                      Compare all →
                    </Link>
                  )}
                </div>

                <ul className="mt-3 space-y-3">
                  {funds.map((f) => {
                    const stale = f.staleness !== "current";
                    return (
                      <li
                        key={f.id}
                        className="rounded-2xl p-5"
                        style={{
                          background: C.card,
                          border: `1px solid ${C.rule}`,
                        }}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0">
                            <h4
                              className="text-[16px] font-bold leading-snug"
                              style={{ fontFamily: "var(--font-display)" }}
                            >
                              {f.name}
                            </h4>
                            <p
                              className="mt-0.5 text-[12.5px]"
                              style={{ color: C.muted }}
                            >
                              {f.provider.name}
                            </p>
                          </div>
                          {f.statedChargesPct && (
                            <div className="text-right">
                              <p className="text-[1.5rem] font-bold tabular-nums leading-none">
                                {f.statedChargesPct.value.toFixed(2)}%
                              </p>
                              <p
                                className="mt-1 text-[10.5px]"
                                style={{ color: C.muted }}
                              >
                                a year in charges
                              </p>
                            </div>
                          )}
                        </div>

                        <dl className="mt-4 flex flex-wrap gap-x-7 gap-y-2 text-[12.5px]">
                          <div className="flex gap-1.5">
                            <dt style={{ color: C.muted }}>Minimum</dt>
                            <dd className="font-semibold tabular-nums">
                              {f.minimumGhs ? GHS.format(f.minimumGhs.value) : "—"}
                            </dd>
                          </div>
                          <div className="flex gap-1.5">
                            <dt style={{ color: C.muted }}>Dealing</dt>
                            <dd className="font-semibold capitalize">
                              {f.dealingFrequency ?? "—"}
                            </dd>
                          </div>
                          {f.statedChargesPct && (
                            <div className="flex gap-1.5">
                              <dt style={{ color: C.muted }}>Confirmed</dt>
                              <dd className="font-semibold">
                                {fmtDate(f.statedChargesPct.asOf)}
                              </dd>
                            </div>
                          )}
                        </dl>

                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          <span
                            className="rounded-full px-2.5 py-1 text-[10.5px] font-semibold"
                            style={{ background: `${C.good}14`, color: C.good }}
                          >
                            ✓ Documents verified
                          </span>
                          <span
                            className="rounded-full px-2.5 py-1 text-[10.5px] font-semibold"
                            style={{
                              background: stale ? `${C.clay}14` : `${C.good}14`,
                              color: stale ? C.clay : C.good,
                            }}
                          >
                            {stale
                              ? `Prices ${Math.round((f.daysSinceLastObservation ?? 0) / 30)} months old`
                              : "Prices current"}
                          </span>
                          {f.feeChanged && (
                            <span
                              className="rounded-full px-2.5 py-1 text-[10.5px] font-semibold"
                              style={{ background: `${C.gold}22`, color: C.ink }}
                            >
                              Charges reduced
                            </span>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
        </div>

        {/* DIRECTORY — condensed. A name with no figures needs a line, not a card. */}
        <h2
          className="mt-14 text-[24px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Awaiting data
        </h2>
        <div
          className="mt-3 rounded-2xl px-5 py-4 text-[13px] leading-relaxed"
          style={{ background: `${C.gold}1A` }}
        >
          <p>
            <strong>
              {directory.length} funds we know exist but can&rsquo;t yet describe.
            </strong>{" "}
            Their managers publish little or nothing publicly, or publish it
            somewhere we can&rsquo;t reach.
          </p>
          <p className="mt-2.5" style={{ color: C.muted }}>
            Names come from a third-party catalogue and{" "}
            <strong>haven&rsquo;t been checked against the SEC register</strong>,
            so some may be out of date. Manage one of these?{" "}
            <a
              href={`mailto:${BRAND.dataEmail}`}
              className="underline underline-offset-2"
              style={{ color: C.deep }}
            >
              Send us your figures
            </a>{" "}
            and we&rsquo;ll publish them instead of our gaps.
          </p>
        </div>

        <div className="mt-6 space-y-7">
          {[...dirByClass.entries()]
            .sort((a, b) => b[1].length - a[1].length)
            .map(([cls, entries]) => (
              <div key={cls}>
                <h3
                  className="text-[12px] font-bold uppercase tracking-wider"
                  style={{ color: C.muted }}
                >
                  {CLASS_LABEL[cls] ?? cls}
                  <span className="ml-2 font-normal opacity-70">
                    {entries.length}
                  </span>
                </h3>
                <ul
                  className="mt-2 overflow-hidden rounded-2xl"
                  style={{ background: C.card, border: `1px solid ${C.rule}` }}
                >
                  {entries.map((d, i) => (
                    <li
                      key={d.id}
                      className="flex items-center justify-between gap-3 px-4 py-2.5 text-[13px]"
                      style={{
                        borderTop: i === 0 ? "none" : `1px solid ${C.rule}`,
                      }}
                    >
                      <span className="min-w-0 truncate font-medium">
                        {d.name}
                      </span>
                      <span
                        className="shrink-0 text-[11px]"
                        style={{ color: C.clay }}
                      >
                        no figures yet
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
        </div>

        <section
          className="mt-14 rounded-3xl p-6 sm:p-8"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2
            className="text-[18px] font-bold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            If you manage one of these funds
          </h2>
          <p className="mt-3 text-[13.5px] leading-relaxed" style={{ color: C.muted }}>
            We publish factual comparisons using each provider&rsquo;s own
            documents, and cite the document and date beside every figure. We
            don&rsquo;t rank by anything you can pay for, and we don&rsquo;t
            charge to be listed. Send your factsheet or price history and
            we&rsquo;ll show your figures instead of our gaps.
          </p>
          <p className="mt-4 text-[14px] font-semibold">
            <a
              href={`mailto:${BRAND.dataEmail}`}
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              {BRAND.dataEmail}
            </a>
          </p>
          <p className="mt-6 text-[11px] leading-relaxed" style={{ color: C.muted }}>
            {BRAND.legalStatus}
          </p>
        </section>

        <nav className="mt-10 flex flex-wrap gap-2">
          {groups.map((g) => (
            <Link
              key={g.peerGroup}
              href={`/compare/${toUrl(g.peerGroup)}`}
              className="rounded-full px-4 py-2 text-[13px] font-semibold"
              style={{
                background: C.card,
                color: C.ink,
                border: `1px solid ${C.rule}`,
              }}
            >
              Compare {g.label.toLowerCase()}
            </Link>
          ))}
        </nav>
      </div>
      <Footer />
    </main>
  );
}
