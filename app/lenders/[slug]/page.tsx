/**
 * app/lenders/[slug]/page.tsx — a bank's own page.
 *
 * THIS IS WHAT AN OUTREACH EMAIL LINKS TO, and that shapes everything.
 *
 * A bank opening it sees: their nine Bank of Ghana reported rates, where each
 * sits against the market, the fees their headline rate hides — and then seven
 * empty fields, because BoG's APR report contains no product terms at all.
 *
 * THE ASK IS STRONGER HERE THAN ON THE FUND SIDE. A fund manager is being told
 * a field is blank. A bank is being shown a regulatory average attached to
 * their name with nothing to explain it. A lender whose reported rate looks
 * high has a reason to send us their actual terms — which is the point.
 *
 * WHAT THE PAGE MUST NOT IMPLY
 *
 *   THAT THE AVERAGE IS A PRODUCT. GCB does not sell "one-year SME credit at
 *   22.3%". That figure is a supervisory statistic covering whatever they
 *   lent. Presenting it as an offer would misrepresent the bank and mislead a
 *   borrower, and it is the mistake most rate-comparison content makes.
 *
 *   THAT A HIGH RATE MEANS A BAD LENDER. A bank lending to riskier borrowers
 *   reports a higher average and may be the only one lending to them at all.
 *   The page reports the number and does not grade anyone on it.
 */

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";
import { notFound } from "next/navigation";

import { BRAND } from "@/lib/brand";
import {
  creditLabel,
  getLender,
  getLenderSlugs,
  getMarketAverages,
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

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export async function generateStaticParams() {
  const slugs = await getLenderSlugs();
  return slugs.map((slug) => ({ slug }));
}

export const revalidate = 3600;

export default async function LenderPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const [lender, averages] = await Promise.all([
    getLender(slug),
    getMarketAverages(),
  ]);
  if (!lender) notFound();

  const missing = lender.disclosed.filter((d) => !d.has);
  const byCategory = new Map<string, typeof lender.products>();
  for (const p of lender.products) {
    if (!byCategory.has(p.category)) byCategory.set(p.category, []);
    byCategory.get(p.category)!.push(p);
  }
  for (const list of byCategory.values()) {
    list.sort((a, b) => a.tenorYears - b.tenorYears);
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
        {lender.products.length} rates published by Bank of Ghana
        {lender.asOf ? ` · ${fmtDate(lender.asOf)}` : ""} · indicative, not
        offers
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
            background: `linear-gradient(135deg, #7A3E12 0%, ${C.gold} 155%)`,
          }}
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-80">
            Lender
          </p>
          <h1
            className="mt-3 text-[2rem] font-bold leading-[1.08] sm:text-[2.7rem]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {lender.name}
          </h1>
          {lender.legalName && lender.legalName !== lender.name && (
            <p className="mt-2 text-[13px] opacity-80">{lender.legalName}</p>
          )}

          <div className="mt-8 grid grid-cols-3 gap-4 sm:max-w-md">
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Rates reported
              </p>
              <p className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]">
                {lender.products.length}
              </p>
            </div>
            {lender.bestApr !== null && (
              <div>
                <p className="text-[10px] uppercase tracking-wider opacity-75">
                  Lowest of theirs
                </p>
                <p className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]">
                  {lender.bestApr.toFixed(2)}%
                </p>
              </div>
            )}
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Product details held
              </p>
              <p className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]">
                0
                <span className="text-[1rem] opacity-60"> of 7</span>
              </p>
            </div>
          </div>

          {lender.website && (
            <p className="mt-7 text-[13px] opacity-90">
              <a
                href={lender.website}
                rel="noopener noreferrer nofollow"
                target="_blank"
                className="underline underline-offset-4"
              >
                {lender.website.replace(/^https?:\/\//, "")}
              </a>
            </p>
          )}
        </section>

        {/* Rates, with market context */}
        <h2
          className="mt-12 text-[24px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What Bank of Ghana reports
        </h2>
        <p className="mt-2 max-w-2xl text-[13.5px]" style={{ color: C.muted }}>
          Average annualised rates across whatever {lender.name} lent in the
          period — a supervisory statistic, not a price list. What a given
          borrower is offered depends on the bank&rsquo;s assessment of them.
        </p>

        <div className="mt-5 space-y-7">
          {[...byCategory.entries()].map(([cat, rows]) => (
            <section key={cat}>
              <h3
                className="text-[13px] font-bold uppercase tracking-wider"
                style={{ color: C.deep }}
              >
                {creditLabel(cat)} credit
              </h3>
              <div
                className="mt-2 overflow-hidden rounded-2xl"
                style={{ background: C.card, border: `1px solid ${C.rule}` }}
              >
                {rows.map((r, i) => {
                  const mkt = averages.get(`${r.category}:${r.tenorYears}`);
                  const vsMarket =
                    mkt && r.aprPct !== null
                      ? Number((r.aprPct - mkt.avg).toFixed(2))
                      : null;
                  return (
                    <div
                      key={r.id}
                      className="px-5 py-4"
                      style={{
                        borderTop: i === 0 ? "none" : `1px solid ${C.rule}`,
                      }}
                    >
                      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                        <span className="text-[13.5px] font-semibold">
                          {r.tenorYears} year{r.tenorYears > 1 ? "s" : ""}
                        </span>
                        <span className="text-[1.25rem] font-bold tabular-nums">
                          {r.aprPct !== null ? `${r.aprPct.toFixed(2)}%` : "—"}
                        </span>
                      </div>
                      <p className="mt-1 text-[12px]" style={{ color: C.muted }}>
                        {r.lendingRatePct !== null && (
                          <>
                            Lending rate {r.lendingRatePct.toFixed(2)}%
                            {r.feeGapPct !== null && r.feeGapPct > 0.05
                              ? `, fees add ${r.feeGapPct.toFixed(2)} points`
                              : ", no additional charges reported"}
                            .{" "}
                          </>
                        )}
                        {vsMarket !== null && mkt && (
                          <span
                            style={{
                              color: vsMarket <= 0 ? C.good : C.clay,
                              fontWeight: 600,
                            }}
                          >
                            {vsMarket === 0
                              ? "At the market average"
                              : vsMarket < 0
                                ? `${Math.abs(vsMarket).toFixed(2)}pp below the ${mkt.count}-bank average`
                                : `${vsMarket.toFixed(2)}pp above the ${mkt.count}-bank average`}
                          </span>
                        )}
                      </p>
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </div>

        {/* What's missing — the reason the page exists */}
        <h2
          className="mt-14 text-[24px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What we don&rsquo;t know about your products
        </h2>
        <p className="mt-2 max-w-2xl text-[13.5px]" style={{ color: C.muted }}>
          Bank of Ghana&rsquo;s report contains averages, not terms. So a
          business reading this page learns what you charged on average and
          nothing about what you actually offer.
        </p>

        <div
          className="mt-5 overflow-hidden rounded-2xl"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          {lender.disclosed.map((d, i) => (
            <div
              key={d.field}
              className="flex items-center justify-between gap-3 px-5 py-3 text-[13.5px]"
              style={{ borderTop: i === 0 ? "none" : `1px solid ${C.rule}` }}
            >
              <span className="font-medium">{d.field}</span>
              <span
                className="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold"
                style={{
                  background: d.has ? `${C.good}14` : `${C.clay}12`,
                  color: d.has ? C.good : C.clay,
                }}
              >
                {d.has ? "✓ Held" : "Not held"}
              </span>
            </div>
          ))}
        </div>

        <section
          className="mt-6 rounded-3xl p-6 sm:p-8"
          style={{ background: C.card, border: `1px solid ${C.gold}` }}
        >
          <h2
            className="text-[19px] font-bold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {missing.length} things we&rsquo;d like from you
          </h2>
          <p
            className="mt-3 max-w-2xl text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            Send your business lending terms — facility names, minimums,
            security, who qualifies, how long a decision takes — and
            we&rsquo;ll publish those alongside the regulatory figures, with
            your document cited and dated. Businesses comparing lenders would
            then see what you actually offer rather than an average.
          </p>
          <p className="mt-5 text-[14px] font-semibold">
            <a
              href={`mailto:${BRAND.dataEmail}?subject=${encodeURIComponent(
                lender.name + " lending terms",
              )}`}
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              {BRAND.dataEmail}
            </a>
          </p>
          <p
            className="mt-5 text-[12.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            We don&rsquo;t charge to be listed, no lender can buy a ranking, and
            we cite the source beside every figure. Corrections are free and
            applied the same day. A higher reported average doesn&rsquo;t make a
            lender worse — it may reflect who you lend to, and we&rsquo;d rather
            publish your explanation than leave the number bare.
          </p>
          <p className="mt-5 text-[11px] leading-relaxed" style={{ color: C.muted }}>
            {BRAND.legalStatus} We are not a credit broker and do not arrange
            finance.
          </p>
        </section>

        <p className="mt-8 text-[13px]">
          <Link
            href="/funding"
            className="underline underline-offset-4"
            style={{ color: C.deep }}
          >
            ← All business credit
          </Link>
        </p>
      </div>
    </main>
  );
}
