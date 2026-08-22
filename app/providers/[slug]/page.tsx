/**
 * app/providers/[slug]/page.tsx — a provider's own page.
 *
 * THIS IS THE PAGE AN OUTREACH EMAIL LINKS TO, and that shapes everything.
 *
 * A fund manager opening it should see, in order: that their funds are listed
 * accurately, exactly which fields are blank, how their disclosure compares to
 * their competitors', and a single clear ask. The point is to make filling the
 * gaps the obvious next move — not to grade them.
 *
 * SO THE DISCLOSURE CHECKLIST IS BUILT ONLY FROM WHAT THEY PUBLISH. Never from
 * a judgement about the firm, never from anything they could dispute. "You do
 * not publish a total expense ratio" is a fact about their factsheet. "Your
 * disclosure is poor" is an opinion, and an opinion invites an argument instead
 * of a spreadsheet.
 *
 * It also has to work for an investor who lands here from the directory, so the
 * funds and figures come first and the provider-facing ask sits at the bottom.
 */

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";
import { notFound } from "next/navigation";

import { BRAND } from "@/lib/brand";
import { getProvider, getProviders } from "@/lib/data/funds";

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

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export async function generateStaticParams() {
  const providers = await getProviders();
  return providers.map((p) => ({ slug: p.slug }));
}

export const revalidate = 3600;

export default async function ProviderPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const provider = await getProvider(slug);
  if (!provider) notFound();

  const all = await getProviders();
  const others = all.filter((p) => p.slug !== slug);
  const missing = provider.disclosed.filter((d) => !d.has);
  const pct = Math.round(provider.disclosureScore * 100);

  // One entry per fund, not per share class.
  const funds = [...new Map(provider.funds.map((f) => [f.name, f])).values()].sort(
    (a, b) =>
      (a.statedChargesPct?.value ?? 99) - (b.statedChargesPct?.value ?? 99),
  );

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div
        className="w-full px-5 py-2 text-center text-[11px] font-medium tracking-wide text-white"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        {provider.observationCount} price points from their own factsheets

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
            Fund manager
          </p>
          <h1
            className="mt-3 text-[2.1rem] font-bold leading-[1.08] sm:text-[2.8rem]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {provider.name}
          </h1>
          {provider.legalName && provider.legalName !== provider.name && (
            <p className="mt-2 text-[13px] opacity-80">{provider.legalName}</p>
          )}

          <div className="mt-8 grid grid-cols-3 gap-4 sm:max-w-md">
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Funds listed
              </p>
              <p className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]">
                {funds.length}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Price points
              </p>
              <p className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]">
                {provider.observationCount}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider opacity-75">
                Fields published
              </p>
              <p
                className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]"
                style={{ color: missing.length === 0 ? C.gold : "#fff" }}
              >
                {pct}%
              </p>
            </div>
          </div>

          {provider.custodian && (
            <p className="mt-7 text-[13px] opacity-85">
              Custodian: {provider.custodian}
            </p>
          )}
        </section>

        {/* Funds */}
        <h2
          className="mt-12 text-[24px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Funds we track
        </h2>
        <ul className="mt-5 space-y-3">
          {funds.map((f) => (
            <li
              key={f.id}
              className="rounded-2xl p-5"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3
                    className="text-[16px] font-bold leading-snug"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    {f.name}
                  </h3>
                  <p className="mt-0.5 text-[12.5px]" style={{ color: C.muted }}>
                    {f.observationCount} price points
                    {f.firstObservation &&
                      ` · ${fmtDate(f.firstObservation)} to ${fmtDate(f.lastObservation!)}`}
                  </p>
                </div>
                {f.statedChargesPct && (
                  <div className="text-right">
                    <p className="text-[1.5rem] font-bold tabular-nums leading-none">
                      {f.statedChargesPct.value.toFixed(2)}%
                    </p>
                    <p className="mt-1 text-[10.5px]" style={{ color: C.muted }}>
                      charges a year
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
                  <dt style={{ color: C.muted }}>Expense ratio</dt>
                  <dd className="font-semibold tabular-nums">
                    {f.lastFullYearTerPct
                      ? `${f.lastFullYearTerPct.value.toFixed(2)}% (${f.lastFullYearTerYear})`
                      : "not published"}
                  </dd>
                </div>
                {f.peerGroup && (
                  <Link
                    href={`/compare/${toUrl(f.peerGroup)}`}
                    className="font-semibold underline underline-offset-4"
                    style={{ color: C.deep }}
                  >
                    Compare →
                  </Link>
                )}
              </dl>
            </li>
          ))}
        </ul>

        {/* Disclosure — facts about their documents, not judgements about them */}
        <h2
          className="mt-14 text-[24px] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What {provider.name} publishes
        </h2>
        <p className="mt-2 text-[13.5px]" style={{ color: C.muted }}>
          Drawn from their own factsheets. A field counts as published if it
          appears for at least one of their funds.
        </p>

        <div
          className="mt-5 overflow-hidden rounded-2xl"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          {provider.disclosed.map((d, i) => (
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
                {d.has ? "✓ Published" : "Not published"}
              </span>
            </div>
          ))}
        </div>

        {/*
          Neutral, not competitive. An earlier version led with "SIMS publishes
          100% against your 75%", which is true and is leverage — but leading a
          stranger with a competitor scoreboard reads as pressure rather than
          information, and pressure invites an argument instead of a
          spreadsheet. The other providers are linked, so anyone who wants the
          comparison can make it themselves.
        */}
        {others.length > 0 && (
          <div
            className="mt-4 rounded-2xl px-5 py-4 text-[13px] leading-relaxed"
            style={{ background: C.card, border: `1px solid ${C.rule}` }}
          >
            <p style={{ color: C.muted }}>
              We apply the same checklist to every manager we track.{" "}
              {others.map((o, i) => (
                <span key={o.slug}>
                  {i > 0 && ", "}
                  <Link
                    href={`/providers/${o.slug}`}
                    className="font-semibold underline underline-offset-2"
                    style={{ color: C.deep }}
                  >
                    {o.name}
                  </Link>
                </span>
              ))}
              {others.length === 1 ? " is" : " are"} also listed.
            </p>
          </div>
        )}

        {/* Publication is a question, not a failing. */}
        {provider.publication.looksPaused && provider.publication.latestDocument && (
          <div
            className="mt-4 rounded-2xl px-5 py-4 text-[13px] leading-relaxed"
            style={{ background: `${C.gold}1A` }}
          >
            <p className="font-semibold">One thing we&rsquo;re unsure about</p>
            <p className="mt-1.5" style={{ color: C.muted }}>
              The most recent factsheet we hold for {provider.name} is{" "}
              <strong>{fmtDate(provider.publication.latestDocument)}</strong>,
              about {provider.publication.monthsSince} months ago. If
              you&rsquo;ve published since, we&rsquo;ve missed it — tell us where
              and we&rsquo;ll pick it up automatically from now on.
            </p>
          </div>
        )}

        {/* The ask */}
        <section
          className="mt-14 rounded-3xl p-6 sm:p-8"
          style={{
            background: C.card,
            border: `1px solid ${missing.length ? C.gold : C.rule}`,
          }}
        >
          <h2
            className="text-[19px] font-bold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {missing.length
              ? `${missing.length} thing${missing.length === 1 ? "" : "s"} we'd like from you`
              : "Everything we need is published"}
          </h2>

          {missing.length > 0 ? (
            <>
              <p
                className="mt-3 text-[13.5px] leading-relaxed"
                style={{ color: C.muted }}
              >
                These fields aren&rsquo;t in the documents we hold, so they show
                as blank beside your funds. Send them and we&rsquo;ll publish
                your figures with the date and document cited, the same as
                everything else here.
              </p>
              <ul className="mt-4 space-y-2">
                {missing.map((m) => (
                  <li
                    key={m.field}
                    className="flex items-center gap-2.5 text-[13.5px] font-medium"
                  >
                    <span
                      aria-hidden
                      className="h-1.5 w-1.5 shrink-0 rounded-full"
                      style={{ background: C.clay }}
                    />
                    {m.field}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p
              className="mt-3 text-[13.5px] leading-relaxed"
              style={{ color: C.muted }}
            >
              Every field a comparison needs appears somewhere in your published
              documents. If anything here is wrong or out of date, tell us and
              we&rsquo;ll correct it.
            </p>
          )}

          <p className="mt-5 text-[14px] font-semibold">
            <a
              href={`mailto:${BRAND.dataEmail}?subject=${encodeURIComponent(provider.name + " fund data")}`}
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
            We don&rsquo;t charge to be listed, don&rsquo;t rank by anything a
            provider can pay for, and cite the source document beside every
            figure. Corrections are free and applied on the same day.
          </p>
          <p className="mt-5 text-[11px] leading-relaxed" style={{ color: C.muted }}>
            {BRAND.legalStatus}
          </p>
        </section>

        <p className="mt-8 text-[13px]">
          <Link
            href="/funds"
            className="underline underline-offset-4"
            style={{ color: C.deep }}
          >
            ← All Ghanaian funds
          </Link>
        </p>
      </div>
    </main>
  );
}
