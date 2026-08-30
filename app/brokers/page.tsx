/**
 * app/brokers/page.tsx — who trades on the Ghana Stock Exchange.
 *
 * THE CENTRAL CLAIM IS NOW CHECKED, NOT ASSUMED
 * This page said none of the twenty-four publishes a commission rate. That
 * rested on the GSE reports and the SEC register — neither of which would
 * carry a rate even if a broker published one on its own site.
 *
 * All twenty-four sites have since been visited. Eighteen were reachable; none
 * published a rate; one, Republic Securities, published a minimum to open an
 * account; three said "competitive rates" without a figure. Six sites did not
 * respond at all.
 *
 * The claim survived the test, which is the only reason it stays on the page.
 * Had one broker published a rate, this would have named them.
 *
 * WHY THIS PAGE EXISTS AT ALL
 * Someone wanting to buy NewGold ETF, or any listed share, must go through a
 * licensed dealing member. There are twenty-four of them. Not one publishes a
 * commission rate, so a saver choosing between them has nothing to compare —
 * no cost, no minimum, no account terms.
 *
 * What the exchange does publish, monthly, is how much business each did. That
 * is a poor proxy for what a saver wants to know, and it is the only public
 * fact there is. Withholding it because it is imperfect would leave people
 * with nothing at all.
 *
 * THE RANGE CARRIES THE MEANING, NOT THE AVERAGE
 * IC Securities: 52.70% average, 19.97% to 78.82% range, fifteen months.
 *
 * Publish the maximum and the exchange looks captured by one firm. Publish the
 * average and it looks like settled leadership. The truth is neither — a
 * fifty-nine point swing with no direction means a handful of block trades
 * decide who leads in any month. That is a fact about how THIN the market is,
 * and it matters more to a saver than any ranking: an index that rose 76% on
 * volume that fell 72% is not a gain you can necessarily sell into.
 *
 * So every figure appears with its range, and the page says plainly that
 * activity is not cost, not quality, and not a recommendation.
 */

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import { BRAND } from "@/lib/brand";
import { getBrokers } from "@/lib/data/funds";

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

const GHS = new Intl.NumberFormat("en-GH", {
  style: "currency",
  currency: "GHS",
  maximumFractionDigits: 0,
  notation: "compact",
});

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export const revalidate = 3600;

export default async function BrokersPage() {
  const brokers = await getBrokers();
  const withData = brokers.filter((b) => b.avgSharePct !== null);
  const months = Math.max(...withData.map((b) => b.monthsObserved ?? 0), 0);
  const top3 = withData
    .slice(0, 3)
    .reduce((sum, b) => sum + (b.avgSharePct ?? 0), 0);
  const leader = withData[0];

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div
        className="w-full px-5 py-2 text-center text-[11px] font-medium tracking-wide text-white"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        {brokers.length} licensed dealing members · we checked every website ·
        none publishes a commission rate
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
            background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 70%)`,
          }}
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-80">
            Ghana Stock Exchange
          </p>
          <h1
            className="mt-3 text-[2.1rem] font-bold leading-[1.08] sm:text-[3rem]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Who actually
            <br />
            trades here
          </h1>

          <div className="mt-8 grid grid-cols-3 gap-4 sm:max-w-lg">
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Licensed members
              </p>
              <p className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]">
                {brokers.length}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Top three do
              </p>
              <p
                className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]"
                style={{ color: C.gold }}
              >
                {top3.toFixed(0)}%
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Publish a rate
              </p>
              <p className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]">
                0
              </p>
            </div>
          </div>

          <p className="mt-7 max-w-xl text-[14px] leading-relaxed opacity-90">
            To buy a listed share or the NewGold ETF you go through one of
            these. What each charges to do it is not published by any of them,
            so what follows is how much business they do — which is the only
            comparable fact there is.
          </p>
        </section>

        {/* The point of the page, said before the list rather than after. */}
        {leader && leader.minSharePct !== null && (
          <section
            className="mt-6 rounded-2xl p-5 sm:p-6"
            style={{ background: C.card, border: `1px solid ${C.gold}` }}
          >
            <p
              className="text-[11px] font-semibold uppercase tracking-[0.16em]"
              style={{ color: C.clay }}
            >
              Read the range, not the average
            </p>
            <p className="mt-2 max-w-2xl text-[13.5px] leading-relaxed">
              {leader.name} averaged{" "}
              <strong>{leader.avgSharePct?.toFixed(2)}%</strong> of value traded
              — but ranged from{" "}
              <strong>{leader.minSharePct.toFixed(2)}%</strong> to{" "}
              <strong>{leader.maxSharePct?.toFixed(2)}%</strong> across{" "}
              {leader.monthsObserved} months. A swing that size with no
              direction means a handful of large trades decide who leads in any
              given month.
            </p>
            <p className="mt-3 text-[12.5px]" style={{ color: C.muted }}>
              That is a fact about how thin this market is, not about how
              dominant any firm is — and thinness is what a saver should weigh.
              The index rose 76% in the year to July 2026 while volume fell 72%.
              A gain in a market that quiet is not necessarily one you can sell
              into.
            </p>
          </section>
        )}

        <h2
          className="mt-12 text-[24px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Share of value traded
        </h2>
        <p className="mt-2 max-w-2xl text-[13.5px]" style={{ color: C.muted }}>
          From the exchange&rsquo;s own monthly reports
          {months > 0 ? `, ${months} of them` : ""}. Ordered by average share.
          This measures activity — not cost, not quality, and not a
          recommendation.
        </p>

        <ol className="mt-5 space-y-2.5">
          {withData.map((b, i) => {
            const width =
              b.avgSharePct !== null && withData[0].avgSharePct
                ? Math.max(2, (b.avgSharePct / withData[0].avgSharePct) * 100)
                : 2;
            return (
              <li
                key={b.slug}
                className="rounded-2xl p-4 sm:p-5"
                style={{
                  background: C.card,
                  border: `1px solid ${i === 0 ? C.gold : C.rule}`,
                }}
              >
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <h3 className="text-[14.5px] font-bold">{b.name}</h3>
                  <span className="text-[1.15rem] font-bold tabular-nums">
                    {b.avgSharePct?.toFixed(2)}%
                  </span>
                </div>

                {/*
                  Value share and volume share point different ways, and the
                  gap is the most useful thing on this page. A firm doing more
                  of the cedis than the shares is handling fewer, larger
                  trades — institutional block business. One doing more of the
                  shares than the cedis is taking smaller orders.

                  No Ghanaian broker publishes whether it wants a GH¢5,000
                  client. This is the nearest the public data gets, and it
                  contradicts the value ranking: Databank sits third on value
                  and second on volume.
                */}
                {b.volumeSharePct !== null && b.avgSharePct !== null && (
                  <p className="mt-1 text-[12.5px]" style={{ color: C.muted }}>
                    {b.volumeSharePct.toFixed(2)}% of shares traded
                    {b.avgSharePct > b.volumeSharePct * 1.15 && (
                      <span style={{ color: C.clay }}>
                        {" "}
                        — fewer, larger trades
                      </span>
                    )}
                    {b.volumeSharePct > b.avgSharePct * 1.15 && (
                      <span style={{ color: C.good }}>
                        {" "}
                        — more trades, smaller ones
                      </span>
                    )}
                  </p>
                )}

                <div
                  className="mt-3 h-1.5 w-full overflow-hidden rounded-full"
                  style={{ background: C.rule }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${width}%`,
                      background: i === 0 ? C.gold : C.teal,
                    }}
                  />
                </div>

                {/*
                  Where to actually reach them. The page previously ranked
                  twenty-four firms by activity and gave no address, phone or
                  website for any of them — telling a saver who is busiest and
                  nothing they could act on. These come from the SEC's
                  broker-dealer register: what each firm filed with its
                  regulator, which is not proof anyone answers the phone.
                */}
                {(b.contactPhone || b.website || b.contactEmail) && (
                  <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[12.5px]">
                    {b.contactPhone && (
                      <a
                        href={`tel:${b.contactPhone.split(/[\/ ]/)[0]}`}
                        style={{ color: C.deep }}
                        className="underline underline-offset-2"
                      >
                        {b.contactPhone}
                      </a>
                    )}
                    {b.website && (
                      <a
                        href={b.website}
                        target="_blank"
                        rel="noopener noreferrer nofollow"
                        style={{ color: C.deep }}
                        className="underline underline-offset-2"
                      >
                        {b.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                      </a>
                    )}
                    {b.contactEmail && (
                      <a
                        href={`mailto:${b.contactEmail}`}
                        style={{ color: C.deep }}
                        className="underline underline-offset-2"
                      >
                        {b.contactEmail}
                      </a>
                    )}
                  </div>
                )}

                {b.officeAddress && (
                  <p className="mt-1.5 text-[12px]" style={{ color: C.muted }}>
                    {b.officeAddress}
                  </p>
                )}

                <p className="mt-2.5 text-[12px]" style={{ color: C.muted }}>
                  {b.minSharePct !== null && b.maxSharePct !== null && (
                    <>
                      Ranged {b.minSharePct.toFixed(2)}% to{" "}
                      {b.maxSharePct.toFixed(2)}%
                    </>
                  )}
                  {b.monthsObserved !== null && (
                    <> across {b.monthsObserved} month
                      {b.monthsObserved === 1 ? "" : "s"}</>
                  )}
                  {b.firstSeen && b.lastSeen && (
                    <>
                      {" "}
                      ({fmtDate(b.firstSeen)} – {fmtDate(b.lastSeen)})
                    </>
                  )}
                  . Commission not published.
                </p>

                {b.valueTradedGhs !== null && b.latestMonth && (
                  <p className="mt-1 text-[12px]" style={{ color: C.muted }}>
                    In {fmtDate(b.latestMonth)} they traded{" "}
                    {GHS.format(b.valueTradedGhs)}
                    {b.volumeTraded !== null && (
                      <> across {b.volumeTraded.toLocaleString()} shares</>
                    )}
                    .
                  </p>
                )}
              </li>
            );
          })}
        </ol>

        <section
          className="mt-12 rounded-3xl p-6 sm:p-8"
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
              <strong style={{ color: C.ink }}>What any of them charge.</strong>{" "}
              We visited all {brokers.length} websites. Not one publishes a
              commission rate. One — Republic Securities — publishes a minimum
              to open an account. Three describe their rates as
              &ldquo;competitive&rdquo; without giving a figure. An
              international platform quotes 0.75% for Ghanaian shares; what a
              member firm in Accra charges is not published anywhere.
            </li>
            <li>
              <strong style={{ color: C.ink }}>
                Six of them have no working website.
              </strong>{" "}
              Bullion Securities, CDH Securities, FirstBanc Brokerage, Petra
              Securities, Sarpong Capital Markets and Strategic African
              Securities did not respond when we checked. All six hold current
              SEC licences. For someone trying to open an account, that is a
              barrier before any question of cost.
            </li>
            <li>
              <strong style={{ color: C.ink }}>
                Whether a busy broker is a good one.
              </strong>{" "}
              Share of value traded reflects who handles large institutional
              orders. It says nothing about service to a retail client with
              GH&#8373;5,000, and should not be read as a ranking.
            </li>
            <li>
              <strong style={{ color: C.ink }}>Months they didn&rsquo;t appear.</strong>{" "}
              A firm observed in three reports is averaged over three, not
              fifteen. That flatters occasional participants against consistent
              ones, so the month count is shown beside every figure.
            </li>
          </ul>

          <p
            className="mt-6 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            <strong style={{ color: C.ink }}>If you run one of these firms:</strong>{" "}
            send us your commission schedule and we&rsquo;ll publish it beside
            your name, cited and dated. We checked all {brokers.length} sites
            and found no rate on any of them, so you would be the first
            Ghanaian broker whose costs a saver could check before opening an
            account — which is a reason to be listed rather than a risk.
          </p>
          <p className="mt-3 text-[14px] font-semibold">
            <a
              href={`mailto:${BRAND.dataEmail}?subject=${encodeURIComponent(
                "Brokerage rates",
              )}`}
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              {BRAND.dataEmail}
            </a>
          </p>

          <p className="mt-6 text-[11px] leading-relaxed" style={{ color: C.muted }}>
            {BRAND.legalStatus} Market share figures are taken from the Ghana
            Stock Exchange&rsquo;s published monthly reports.
          </p>
        </section>

        <p className="mt-8 text-[13px]">
          <Link
            href="/compare/commodity-GHS"
            className="underline underline-offset-4"
            style={{ color: C.deep }}
          >
            ← Gold, including the NewGold ETF
          </Link>
        </p>
      </div>
    </main>
  );
}
