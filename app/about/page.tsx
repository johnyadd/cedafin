import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import { BRAND } from "@/lib/brand";

/**
 * app/about/page.tsx — who is behind this, and how it works.
 *
 * WHY THIS PAGE EXISTS
 * Everything here was already said somewhere: the method on /methodology,
 * the free-to-quote terms on /for-journalists, the consulting on
 * /work-with-us, the regulatory line in every footer. A reader deciding
 * whether to trust a financial site should not have to assemble that
 * themselves.
 *
 * WHY IT LEADS WITH WHAT CEDAFIN OFFERS
 * An About page is about Cedafin. What providers do and do not publish is a
 * finding, and it has its own page at /what-gets-published; it does not need
 * to open this one.
 *
 * WHAT IT DELIBERATELY DOES NOT CLAIM
 * No advertising site-wide — the decision is that comparison pages carry
 * none, and that is what it says. No company registration details it has not
 * been given. No update frequency the pipeline does not actually keep: gold
 * is priced "on each working day Bank of Ghana publishes", because since
 * 2 September 2026 Bank of Ghana has not.
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
  good: "#0E8F62",
  bg: "#F2F6F9",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
};

export const metadata = {
  title: "About Cedafin — who runs it, how it works, and who pays",
  description:
    "Cedafin puts Ghanaian savings, investment and borrowing options side by side, every figure dated and sourced. Who runs it, how the figures are produced, how often they update, and how the consulting is kept apart from the research.",
};

const OFFERS: [string, string, string][] = [
  ["/funds", "Funds", "Charges, minimums and returns, with each figure's source and date"],
  ["/treasury-bill-calculator", "Treasury bills", "This week's auction rates, and what a bill would pay you"],
  ["/shares", "Listed shares", "Every company on the Ghana Stock Exchange, with price history"],
  ["/compare/commodity-GHS", "Gold", "The coins and the ETF, and what the currency did to them"],
  ["/savings", "Savings accounts", "What banks pay, and the conditions that come with it"],
  ["/funding", "Business credit", "What loans actually cost at every licensed bank"],
  ["/mortgages", "Mortgages", "Published rates and terms for buying a home in Ghana"],
  ["/investing-from-abroad", "Investing from abroad", "Which providers say they will open an account from outside Ghana"],
];

const SCHEDULE: [string, string][] = [
  ["Treasury bill rates", "Weekly, after each Friday auction, from Bank of Ghana's rates table"],
  ["Gold coin prices", "On each working day Bank of Ghana publishes a pricing circular"],
  ["Listed shares", "Monthly, from the Ghana Stock Exchange's own report"],
  ["Bank lending rates", "Monthly, from the return Bank of Ghana requires banks to file"],
  ["Regulators' registers", "Snapshotted on the first of every month, and compared with the month before"],
  ["Fund charges and prices", "As fund managers publish factsheets, collected and checked by hand"],
  ["Consistency checks", "Every day — freshness, implausible prices, and figures without a source"],
];

function H2({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="mt-12 text-[1.5rem] font-bold"
      style={{ fontFamily: "var(--font-display)" }}
    >
      {children}
    </h2>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="mt-3 text-[15.5px] leading-relaxed">{children}</p>;
}

function A({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="font-semibold underline underline-offset-4"
      style={{ color: C.deep }}
    >
      {children}
    </Link>
  );
}

export default function AboutPage() {
  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div className="mx-auto max-w-3xl px-5 py-10 sm:px-8 sm:py-12">
        <p
          className="text-[11px] font-semibold uppercase tracking-[0.16em]"
          style={{ color: C.gold }}
        >
          About Cedafin
        </p>
        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.1] sm:text-[2.4rem]"
          style={{ fontFamily: "var(--font-display)", letterSpacing: "-0.02em" }}
        >
          Ghana&rsquo;s savings, investment and borrowing options, side by side
        </h1>
        <p className="mt-5 text-[16.5px] leading-relaxed" style={{ color: C.muted }}>
          Cedafin lets you compare what Ghanaian financial products cost and
          return before you commit money — every figure taken from the
          provider&rsquo;s or regulator&rsquo;s own documents, dated, and linked
          to where it came from.
        </p>

        <H2>What you can do here</H2>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {OFFERS.map(([href, title, what]) => (
            <Link
              key={href}
              href={href}
              className="block rounded-2xl p-4 transition-shadow hover:shadow-md"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <p className="text-[14.5px] font-bold" style={{ color: C.deep }}>
                {title} &rarr;
              </p>
              <p className="mt-1 text-[13px] leading-relaxed" style={{ color: C.muted }}>
                {what}
              </p>
            </Link>
          ))}
        </div>
        <P>
          Where the data allows, returns are shown after inflation as well as
          before, so you can see what your money gained in buying power and not
          just in cedis. And every page says how current its figures are.
        </P>

        <H2>Who runs it</H2>
        <P>
          Cedafin is run by John Addae. His background is in financial planning
          and analysis and in data engineering, and he holds a BSc in Computer
          Science and an MBA in Finance.
        </P>
        <P>
          That background is visible in how the site works. Figures are read
          from source documents by deterministic parsing rather than typed in or
          estimated, so the same document always gives the same answer. Every
          figure carries the date it was published and a link back to where it
          came from. And the site checks itself daily for figures that have
          stopped updating, prices that move implausibly, and anything without a
          source.
        </P>

        <H2>How the figures are produced</H2>
        <P>
          From the providers&rsquo; own published material and from the
          regulators: Bank of Ghana, the Securities and Exchange Commission, the
          Ghana Stock Exchange and the Ghana Statistical Service. Where a figure
          has not been published, the field is shown blank with the date we
          looked, so you always know what was checked.
        </P>
        <P>
          The full method, including what counts as verified, is on the{" "}
          <A href="/methodology">methodology page</A>. A provider-by-provider
          record of what each one publishes is on{" "}
          <A href="/what-gets-published">what gets published</A>.
        </P>

        <H2>Every source, kept</H2>
        <P>
          Cedafin keeps a copy of every document its figures come from —
          regulator returns, factsheets, auction results and circulars. The{" "}
          <A href="/the-archive">archive</A> means any figure on the site can be
          checked against its original, including after the publisher has
          replaced it with a newer version.
        </P>

        <H2>How often it updates</H2>
        <div
          className="mt-4 overflow-hidden rounded-2xl"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          {SCHEDULE.map(([what, when], i) => (
            <div
              key={what}
              className="flex flex-col gap-1 p-4 sm:flex-row sm:gap-6"
              style={{ borderTop: i === 0 ? "none" : `1px solid ${C.rule}` }}
            >
              <p className="text-[14px] font-bold sm:w-48 sm:shrink-0">{what}</p>
              <p className="text-[14px] leading-relaxed" style={{ color: C.muted }}>
                {when}
              </p>
            </div>
          ))}
        </div>

        <H2>Corrections</H2>
        <P>
          Corrections are free and applied the same day. Providers can send
          their charges, minimums or account terms at any time, and they go on
          their page cited and dated. Past corrections are listed openly on the{" "}
          <A href="/methodology">methodology page</A>.
        </P>

        <H2>Who pays</H2>
        <div
          className="mt-4 overflow-hidden rounded-2xl"
          style={{ background: C.card, border: `1px solid ${C.good}` }}
        >
          <div className="flex">
            <span className="w-1 shrink-0" style={{ background: C.good }} aria-hidden="true" />
            <div className="flex-1 p-5">
              <p className="text-[15px] font-bold">
                No provider pays to be listed, ranked or described
              </p>
              <p className="mt-2 text-[14px] leading-relaxed" style={{ color: C.muted }}>
                There is no paid placement, no referral fee from providers and no
                commission on anything a reader buys. The comparison pages carry
                no advertising. A provider&rsquo;s position on a page is decided
                by its published figures and nothing else.
              </p>
            </div>
          </div>
        </div>

        <H2>How the consulting is kept apart</H2>
        <P>
          Cedafin also works with organisations, helping them turn documents and
          data into figures they can trace and defend. That work is described
          on <A href="/work-with-us">work with us</A>, and it is how the site is
          funded.
        </P>
        <P>
          It does not touch the research. Consulting clients receive no
          different treatment on the comparison pages, no advance sight of
          findings, and no say over what is published about them. If a
          consulting client is ever also a provider shown on this site, that
          will be stated on their page.
        </P>

        <H2>Using what is here</H2>
        <P>
          Everything on the site is free to quote without asking. No permission
          is needed and no credit is required, though every page offers a
          ready-made citation. Journalists who need a figure or a series can
          start at <A href="/for-journalists">for journalists</A>.
        </P>

        <H2>Regulatory status</H2>
        <p className="mt-3 text-[15px] leading-relaxed" style={{ color: C.muted }}>
          {BRAND.legalStatus}
        </p>

        <H2>Contact</H2>
        <P>
          Data, figures and corrections:{" "}
          <a
            href="mailto:data@cedafin.com"
            className="font-semibold underline underline-offset-4"
            style={{ color: C.deep }}
          >
            data@cedafin.com
          </a>
          . Everything else:{" "}
          <a
            href="mailto:enquiries@cedafin.com"
            className="font-semibold underline underline-offset-4"
            style={{ color: C.deep }}
          >
            enquiries@cedafin.com
          </a>
          .
        </P>
      </div>

      <Footer />
    </main>
  );
}
