/**
 * app/page.tsx — the home page.
 *
 * INVESTOR FIRST. The provider pages already do the provider job well, and a
 * site that looks industry-facing won't build the readership that makes
 * providers care about being listed. So this leads with the question a
 * Ghanaian saver actually has — what does this cost me — and puts the
 * provider ask at the bottom.
 *
 * IT LEADS WITH THE COVERAGE GAP, WHICH IS UNUSUAL. Most comparison sites hide
 * how little they cover. Stating "7 verified, 65 still being chased" up front
 * costs something with an investor, and buys something more valuable: it is the
 * line that makes a fund manager click, and it is consistent with a site whose
 * entire proposition is that its numbers can be trusted. A directory that
 * hides its gaps has already told you what kind of source it is.
 *
 * THE AUDIENCE SECTION says what is established and what is not, per audience.
 * The Ghana Card route for the diaspora is real and documented — NIA runs a
 * digital-first process through 11 missions abroad — but the card unlocks
 * IDENTITY, not the whole chain. Card, then a Ghanaian bank account or mobile
 * money, then the fund. Each link needs verifying and none of it is mapped
 * publicly, so the page says so rather than implying a clear path.
 */

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import { BRAND } from "@/lib/brand";
import { getDirectory, getPeerGroups, getPublishedFunds } from "@/lib/data/funds";

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

const toUrl = (peerGroup: string) => peerGroup.replace(/:([^:]*)$/, "-$1");

export const revalidate = 3600;

export default async function HomePage() {
  const [funds, directory, groups] = await Promise.all([
    getPublishedFunds(),
    getDirectory(),
    getPeerGroups(),
  ]);

  const unique = [
    ...new Map(funds.map((f) => [`${f.provider.slug}::${f.name}`, f])).values(),
  ];
  const charges = unique
    .map((f) => f.statedChargesPct?.value)
    .filter((v): v is number => typeof v === "number");
  const cheapest = charges.length ? Math.min(...charges) : null;
  const dearest = charges.length ? Math.max(...charges) : null;
  const lowestMin = unique
    .map((f) => f.minimumGhs?.value)
    .filter((v): v is number => typeof v === "number")
    .sort((a, b) => a - b)[0];
  const total = unique.length + directory.length;

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div
        className="w-full px-5 py-2 text-center text-[11px] font-medium tracking-wide text-white"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        {total} funds on Ghana&rsquo;s SEC register · {unique.length} with
        verified charges · every figure dated
      </div>

      <header className="mx-auto max-w-4xl px-5 pt-6 sm:px-8">
        <span
          className="text-[19px] font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: C.deep }}
        >
          {BRAND.name}
        </span>
      </header>

      <div className="mx-auto max-w-4xl px-5 py-8 sm:px-8 sm:py-10">
        <section
          className="overflow-hidden rounded-3xl p-7 text-white sm:p-12"
          style={{
            background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 62%, ${C.gold} 190%)`,
          }}
        >
          <h1
            className="text-[2.2rem] font-bold leading-[1.06] sm:text-[3.4rem]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Before you invest,
            <br />
            see what it costs.
          </h1>
          <p className="mt-6 max-w-xl text-[15px] leading-relaxed opacity-90">
            Every fund on Ghana&rsquo;s SEC register, in one place. We read the
            providers&rsquo; own factsheets and publish the charges, minimums and
            access terms — with the document and the date beside every figure.
          </p>

          {cheapest !== null && (
            <div className="mt-9 grid grid-cols-2 gap-5 sm:max-w-lg sm:grid-cols-3">
              <div>
                <p className="text-[10px] uppercase tracking-wider opacity-75">
                  Charges range from
                </p>
                <p
                  className="mt-1 text-[1.7rem] font-bold tabular-nums leading-none sm:text-[2.1rem]"
                  style={{ color: C.gold }}
                >
                  {cheapest.toFixed(2)}%
                </p>
                <p className="mt-1 text-[11px] opacity-70">
                  up to {dearest!.toFixed(2)}% a year
                </p>
              </div>
              {lowestMin !== undefined && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider opacity-75">
                    Start from
                  </p>
                  <p className="mt-1 text-[1.7rem] font-bold tabular-nums leading-none sm:text-[2.1rem]">
                    {GHS.format(lowestMin)}
                  </p>
                  <p className="mt-1 text-[11px] opacity-70">lowest minimum</p>
                </div>
              )}
              <div>
                <p className="text-[10px] uppercase tracking-wider opacity-75">
                  Verified so far
                </p>
                <p className="mt-1 text-[1.7rem] font-bold tabular-nums leading-none sm:text-[2.1rem]">
                  {unique.length}
                  <span className="text-[1.1rem] opacity-60"> of {total}</span>
                </p>
                <p className="mt-1 text-[11px] opacity-70">
                  {directory.length} still being chased
                </p>
              </div>
            </div>
          )}

          <div className="mt-9 flex flex-wrap gap-3">
            {groups.slice(0, 2).map((g) => (
              <Link
                key={g.peerGroup}
                href={`/compare/${toUrl(g.peerGroup)}`}
                className="rounded-full px-5 py-2.5 text-[13.5px] font-bold"
                style={{ background: "#fff", color: C.deep }}
              >
                Compare {g.label.toLowerCase()} →
              </Link>
            ))}
          </div>
        </section>

        {/* Who this is for */}
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
              detail: `All the figures on this site are for you. The lowest minimum we've found is ${lowestMin !== undefined ? GHS.format(lowestMin) : "small"}, and most funds deal daily.`,
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

        {/* How this is different */}
        <h2
          className="mt-14 text-[24px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Why trust these numbers
        </h2>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {[
            {
              t: "Every figure is dated",
              d: "Each charge and price shows the document it came from and when it was last confirmed. If a number is six months old, we say so instead of hiding it.",
            },
            {
              t: "Like compared with like",
              d: "Not every provider publishes an expense ratio, so we compare on management plus custody — the charges all of them disclose.",
            },
            {
              t: "Nobody can pay for position",
              d: "We don't charge to be listed and no provider can buy a ranking. Cheapest first, and we say when a group is too small to rank at all.",
            },
            {
              t: "Gaps are shown, not hidden",
              d: `${directory.length} funds are listed with no figures because their managers publish little publicly. Leaving them out would make our coverage look better than it is.`,
            },
          ].map((x) => (
            <div
              key={x.t}
              className="rounded-2xl p-5"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <h3 className="text-[14.5px] font-bold">{x.t}</h3>
              <p
                className="mt-1.5 text-[12.5px] leading-relaxed"
                style={{ color: C.muted }}
              >
                {x.d}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/funds"
            className="rounded-full px-5 py-2.5 text-[13.5px] font-bold text-white"
            style={{ background: C.deep }}
          >
            See all {total} funds →
          </Link>
          {groups.map((g) => (
            <Link
              key={g.peerGroup}
              href={`/compare/${toUrl(g.peerGroup)}`}
              className="rounded-full px-4 py-2.5 text-[13px] font-semibold"
              style={{
                background: C.card,
                color: C.ink,
                border: `1px solid ${C.rule}`,
              }}
            >
              {g.label}
            </Link>
          ))}
        </div>

        {/* Provider ask — last, deliberately */}
        <section
          className="mt-14 rounded-3xl p-6 sm:p-8"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2
            className="text-[18px] font-bold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            If you run one of these funds
          </h2>
          <p
            className="mt-3 max-w-2xl text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            We publish from your own documents and cite them beside every figure.
            If your fund is listed with blanks against it, send your factsheet or
            price history and we&rsquo;ll show your figures instead of our gaps.
            Corrections are free and applied the same day.
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
            {BRAND.legalStatus} Past performance does not predict future returns,
            and the value of an investment can fall as well as rise.
          </p>
        </section>
      </div>
    </main>
  );
}
