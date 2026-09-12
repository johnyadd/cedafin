import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import { BRAND } from "@/lib/brand";
import { getTbillRates } from "@/lib/data/funds";

/**
 * app/is-it-licensed/page.tsx
 *
 * WHY THIS PAGE, AND WHY IT IS NOT A HOW-TO
 * The weak version of this page explains how to search the regulators'
 * registers. That tells a reader to do work we have already done — we went
 * through every register to build this site, and the result is the catalogue.
 *
 * So the page starts from what we hold. A hundred and six funds, twenty-four
 * brokers, twenty-two banks, twenty-six savings and loans companies, nine
 * private funds — every one of them taken from a regulator's own register.
 * Which means the fastest check available to a Ghanaian is: search this site.
 *
 * THE CAVEAT THAT RUNS THROUGH IT
 * Absence from our catalogue is a prompt to look harder, never a verdict. New
 * licences are granted, registers change, and we may simply have missed one.
 * A page that let a reader conclude "not on Cedafin means fraudulent" would be
 * doing the same thing as the sites it warns about: asserting more than the
 * evidence carries.
 *
 * WHY NO SITE IS NAMED
 * We have seen platforms advertising returns no Ghanaian instrument produces.
 * No regulator has published a notice about them, and a comparison site
 * accusing a named business of fraud on its own judgement would be wrong
 * however compelling the arithmetic. The test protects a reader either way.
 */

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
};

export const metadata = {
  title: "Is it licensed? — checking a Ghanaian investment platform",
  description:
    "We took every Ghanaian fund, broker, bank and lender from its regulator's own register. The quickest check is to search this site — and here is what a licence does and does not tell you.",
  keywords: [
    "is it licensed Ghana",
    "SEC Ghana licensed fund managers",
    "Ghana investment scam check",
    "licensed stockbrokers Ghana",
    "check investment company Ghana",
  ],
};

const FAQ = [
  {
    q: "How do I check if an investment company is licensed in Ghana?",
    a: "Search this site first — every fund, broker, bank and lender we list was taken from a regulator's own register. If the name is not here, check the Securities and Exchange Commission register at licensees.sec.gov.gh for fund managers and brokers, or Bank of Ghana's registers for banks and savings and loans companies.",
  },
  {
    q: "What return is realistic in Ghana?",
    a: "Government Treasury bills are the benchmark and are published weekly by Bank of Ghana. A licensed money market fund holds much the same instruments and charges around 2% a year, so it returns a little less. Anything promising several times that, or paying weekly, is promising something this market does not produce.",
  },
  {
    q: "Does a licence mean my money is safe?",
    a: "No. A licence means the firm is supervised, files returns and can be sanctioned. It does not guarantee a return or protect you from loss. Licensed Ghanaian institutions failed in the 2017-2019 financial sector clean-up and investors lost money.",
  },
  {
    q: "What if a platform uses the name of a company I recognise?",
    a: "Check the web address, not the name. A name can be copied; a domain cannot be shared. If a platform uses a familiar brand on an unfamiliar address, contact the firm through the details on their own site before sending anything.",
  },
];

export const revalidate = 3600;

export default async function IsItLicensedPage() {
  const rates = await getTbillRates();
  const tbill = rates.find((r) => r.days === 91) ?? rates[0] ?? null;

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            mainEntity: FAQ.map(({ q, a }) => ({
              "@type": "Question",
              name: q,
              acceptedAnswer: { "@type": "Answer", text: a },
            })),
          }),
        }}
      />

      <div className="mx-auto max-w-3xl px-5 py-10 sm:px-8 sm:py-12">
        <p
          className="text-[11px] font-semibold uppercase tracking-[0.16em]"
          style={{ color: C.gold }}
        >
          Before you send money
        </p>
        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.1] sm:text-[2.4rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.02em",
          }}
        >
          Is it licensed?
        </h1>
        <p
          className="mt-5 text-[16.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          We built this site by going through the regulators&rsquo; registers,
          one entry at a time. That work is already done, so the quickest check
          available to you is to search what came out of it.
        </p>

        {/* The service, first. This is what distinguishes the page from a
            how-to guide: the checking has been done. */}
        <section
          className="mt-7 overflow-hidden rounded-2xl"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <div
            className="px-5 py-3 text-white"
            style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em]">
              What we have already checked
            </p>
          </div>
          <div className="p-5">
            <div className="grid gap-2 sm:grid-cols-2">
              {(
                [
                  ["106 funds", "SEC register of licensed collective investment schemes"],
                  ["24 stockbrokers", "SEC register of licensed dealing members"],
                  ["22 banks", "Bank of Ghana APR returns and register"],
                  ["26 savings and loans companies", "Bank of Ghana register"],
                  ["9 private funds", "SEC register of licensed private funds"],
                  ["39 listed companies", "Ghana Stock Exchange monthly reports"],
                ] as [string, string][]
              ).map(([count, source]) => (
                <div
                  key={count}
                  className="rounded-xl p-3.5"
                  style={{ background: C.bg, border: `1px solid ${C.rule}` }}
                >
                  <p className="text-[13.5px] font-bold">{count}</p>
                  <p className="mt-0.5 text-[12px]" style={{ color: C.muted }}>
                    {source}
                  </p>
                </div>
              ))}
            </div>
            <p
              className="mt-4 text-[13.5px] leading-relaxed"
              style={{ color: C.muted }}
            >
              Every provider on this site came off one of those registers. None
              was added because it advertised, asked, or paid — no provider can
              pay to appear here.
            </p>
          </div>
        </section>

        <h2
          className="mt-10 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          So the first check takes a few seconds
        </h2>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          Look for the firm&rsquo;s name on this site. If it is here, it was on
          a regulator&rsquo;s register when we read it, and the page says which
          one and when.
        </p>

        <div
          className="mt-4 rounded-2xl p-5"
          style={{ background: "#FFF8EC", border: `1px solid ${C.gold}` }}
        >
          <p className="text-[14px] font-bold">
            If the name is not here, that is a reason to look harder — not proof
            of anything
          </p>
          <p
            className="mt-2 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            Licences are granted, registers change, and we may simply have
            missed one. What it means is that we did not find the name where we
            would expect to, which is worth ten more minutes before you send
            money rather than after.
          </p>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          {(
            [
              ["/funds", "106 funds", "Every licensed scheme we found"],
              ["/brokers", "24 brokers", "Every licensed dealing member"],
              ["/funding", "22 banks + 26 lenders", "Everyone regulated to lend"],
            ] as [string, string, string][]
          ).map(([href, title, note]) => (
            <Link
              key={href}
              href={href}
              className="rounded-2xl p-4 transition-shadow hover:shadow-md"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <span className="block text-[13.5px] font-bold">{title}</span>
              <span
                className="mt-0.5 block text-[12px] leading-relaxed"
                style={{ color: C.muted }}
              >
                {note}
              </span>
            </Link>
          ))}
        </div>

        {/* The arithmetic. The most useful test on the page, because it needs
            no register at all. */}
        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          The test that needs no register
        </h2>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          Ghana has a risk-free rate, and everything else is priced against it.
          {tbill && (
            <>
              {" "}
              The {tbill.days}-day Government Treasury bill last cleared at{" "}
              <strong>{tbill.ratePct.toFixed(2)}% a year</strong>
              {tbill.asOf ? ` (${tbill.asOf})` : ""}.
            </>
          )}
        </p>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          A licensed money market fund holds much the same instruments and
          charges around 2% a year to do it, so it returns a little less than
          the bill. That is the shape of the market.
        </p>

        <div
          className="mt-5 overflow-hidden rounded-2xl"
          style={{ background: C.card, border: `1px solid ${C.clay}` }}
        >
          <div className="flex">
            <span className="w-1 shrink-0" style={{ background: C.clay }} aria-hidden="true" />
            <div className="flex-1 p-5">
              <p className="text-[14.5px] font-bold">
                So a weekly return is the clearest warning there is
              </p>
              <p
                className="mt-2 text-[14px] leading-relaxed"
                style={{ color: C.muted }}
              >
                Ghanaian instruments pay on a fixed date — a Treasury bill at
                maturity, a fund when you redeem. A platform promising a
                percentage every week is describing something no licensed
                Ghanaian product does, at a rate the market does not produce.
                Ten per cent a week compounds to more than a hundredfold in a
                year.
              </p>
              <p
                className="mt-2.5 text-[14px] leading-relaxed"
                style={{ color: C.muted }}
              >
                It does not matter how professional the website looks, how many
                investors it claims, or whose name is on it. The arithmetic is
                the tell.
              </p>
            </div>
          </div>
        </div>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Check the address, not the name
        </h2>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          A name can be copied. A web address cannot be shared. If a platform
          uses a brand you recognise on an address you do not, treat them as
          different things until you have established otherwise — and establish
          it by contacting the firm through the details on{" "}
          <em>their own</em> site, not the details on the platform.
        </p>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          The provider pages on this site carry the website we found on the
          regulator&rsquo;s register, with the date we checked it.
        </p>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What a licence does not mean
        </h2>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          <strong>It does not mean safe.</strong> A licence means the firm is
          supervised, files returns and can be sanctioned. It is not a
          guarantee, and it never has been anywhere. Lehman Brothers was
          regulated. Northern Rock was regulated. Every bank that failed in
          2008 held every licence it needed, and depositors and investors in
          Ghana lost money in the sector clean-up of 2017 to 2019 for the same
          reason: supervision is not solvency.
        </p>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          What a licence does do is give you somewhere to complain, a body that
          can investigate, and a firm with something to lose. That is worth a
          great deal against a platform with none of it — which is the
          comparison that matters here, rather than licensed against safe.
        </p>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          <strong>And it does not mean cheap.</strong> Licensed funds on this
          site charge between nothing and 2.65% a year, and most Ghanaian
          providers publish no charge at all. Being regulated and being good
          value are separate questions.
        </p>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Checking it yourself
        </h2>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          The registers are public. If you would rather go to the source — and
          for anything important you should — these are the ones we use.
        </p>
        <div className="mt-4 space-y-2">
          {(
            [
              [
                "Securities and Exchange Commission",
                "licensees.sec.gov.gh",
                "https://licensees.sec.gov.gh/",
                "Fund managers, unit trusts, stockbrokers, custodians, private funds, investment advisers",
              ],
              [
                "Bank of Ghana",
                "bog.gov.gh",
                "https://www.bog.gov.gh/supervision-regulation/registered-institutions/",
                "Banks, savings and loans companies, finance houses, microfinance institutions",
              ],
              [
                "Ghana Stock Exchange",
                "gse.com.gh",
                "https://gse.com.gh/",
                "Listed companies and licensed dealing members",
              ],
            ] as [string, string, string, string][]
          ).map(([name, domain, href, covers]) => (
            <div
              key={name}
              className="rounded-2xl p-4"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <p className="flex flex-wrap items-baseline gap-x-2 text-[13.5px]">
                <strong>{name}</strong>
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[12px] underline underline-offset-4"
                  style={{ color: C.deep }}
                >
                  {domain}
                </a>
              </p>
              <p className="mt-1 text-[12.5px]" style={{ color: C.muted }}>
                {covers}
              </p>
            </div>
          ))}
        </div>

        <section className="mt-12">
          <h2
            className="text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: C.gold }}
          >
            Questions people ask
          </h2>
          <div className="mt-3 space-y-2.5">
            {FAQ.map(({ q, a }) => (
              <details
                key={q}
                className="group rounded-2xl p-4"
                style={{ background: C.card, border: `1px solid ${C.rule}` }}
              >
                <summary className="cursor-pointer list-none text-[13.5px] font-bold">
                  <span className="flex items-start gap-2">
                    <span
                      className="mt-0.5 shrink-0 text-[12px] transition-transform group-open:rotate-90"
                      style={{ color: C.gold }}
                      aria-hidden="true"
                    >
                      &#9656;
                    </span>
                    <span>{q}</span>
                  </span>
                </summary>
                <p
                  className="mt-2.5 pl-5 text-[13px] leading-relaxed"
                  style={{ color: C.muted }}
                >
                  {a}
                </p>
              </details>
            ))}
          </div>
        </section>

        <p className="mt-10 text-[12.5px] leading-relaxed" style={{ color: C.muted }}>
          {BRAND.legalStatus} We name no platform as fraudulent. Where a
          regulator publishes a warning we will report it; until then, the tests
          above are what we can offer, and they work whoever is asking.
        </p>
      </div>

      <Footer />
    </main>
  );
}
