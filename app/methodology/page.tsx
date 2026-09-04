import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import { BRAND } from "@/lib/brand";

/**
 * app/methodology/page.tsx — how every figure here got here.
 *
 * WHY THIS PAGE EXISTS
 * The site's argument is that its figures can be traced. That claim was made
 * in a dozen footers and never in one place, which meant a reader deciding
 * whether to trust it had to assemble the answer themselves.
 *
 * It also matters commercially. We have written to twenty-odd institutions
 * asking for their data. Some will look us up before replying, and a fund
 * manager deciding whether to send a factsheet wants to know what happens to
 * it — how it is cited, whether it is checked, and what we do when it turns
 * out to be wrong.
 *
 * WHY THE MISTAKES ARE ON IT
 * The section listing corrections is the most useful part. Anybody can assert
 * rigour; showing four occasions where a published claim was wrong and what
 * was done about it is evidence. It also sets the expectation that a fifth
 * will happen, which is true.
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

const SOURCES: [string, string][] = [
  [
    "Bank of Ghana",
    "Treasury bill tender results, Annual Percentage Rate returns filed by every bank, daily interbank exchange rates, and the daily Ghana Gold Coin pricing circulars.",
  ],
  [
    "Ghana Stock Exchange",
    "Monthly market reports — share prices, index levels, volumes, and each licensed dealing member's share of value and volume traded.",
  ],
  [
    "Securities and Exchange Commission",
    "Registers of licensed fund managers, broker-dealers and collective investment schemes.",
  ],
  [
    "Fund managers and banks",
    "Their own published factsheets, rate cards and terms, cited by document and date.",
  ],
];


export const metadata = {
  title: "How Cedafin sources its figures — methodology",
  description:
    "Where every number on this site comes from, what counts as verified, and what happens when a provider publishes nothing.",
};

export default function MethodologyPage() {
  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div className="mx-auto max-w-3xl px-5 py-10 sm:px-8 sm:py-14">
        <h1
          className="text-[2rem] font-bold leading-[1.1] sm:text-[2.6rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.02em",
          }}
        >
          How we get our figures
        </h1>
        <p
          className="mt-5 text-[17px] leading-relaxed"
          style={{ color: C.muted }}
        >
          Every number on this site comes from a document its issuer published.
          Where something is not published, the page says so rather than filling
          the gap. This explains how that works in practice — and where we have
          got it wrong.
        </p>

        <hr
          className="mt-8 w-14"
          style={{ borderColor: C.gold, borderTopWidth: "3px" }}
        />

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Where the figures come from
        </h2>
        <ul className="mt-5 space-y-5">
          {SOURCES.map(([name, what]) => (
            <li key={name}>
              <p className="text-[15px] font-bold">{name}</p>
              <p
                className="mt-1 text-[15px] leading-relaxed"
                style={{ color: C.muted }}
              >
                {what}
              </p>
            </li>
          ))}
        </ul>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What counts as verified
        </h2>
        <p className="mt-4 text-[16px] leading-relaxed">
          A figure appears on this site only when we hold the document it came
          from and can name the date it was true. Not a press report of a
          figure, not a number quoted on a third-party page, and not an
          estimate.
        </p>
        <p className="mt-4 text-[16px] leading-relaxed">
          The consequence is visible everywhere. We have catalogued{" "}
          <strong>75 Ghanaian funds and publish complete figures for eight</strong>.
          The other 67 are listed with the fields blank. That is not a gap we
          are hiding — it is the policy working, and closing it depends on
          managers publishing more than they currently do.
        </p>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What happens when nothing is published
        </h2>
        <p className="mt-4 text-[16px] leading-relaxed">
          The field stays blank and the page says why. &ldquo;Not
          published&rdquo; is itself information: an investor deciding between
          two brokers learns something real from the fact that neither states a
          commission rate.
        </p>
        <p className="mt-4 text-[16px] leading-relaxed">
          We do not fill gaps with sector averages, with figures from a similar
          product, or with numbers a provider gave verbally. If we cannot cite
          it, we do not show it.
        </p>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Dates, and why every figure carries one
        </h2>
        <p className="mt-4 text-[16px] leading-relaxed">
          Rates move. Treasury bills change weekly, the gold premium daily, fund
          charges rarely. A figure without a date is a claim about now that was
          true at some point in the past, and it ages silently.
        </p>
        <p className="mt-4 text-[16px] leading-relaxed">
          So every figure is dated, and articles containing rate-sensitive
          numbers carry the date those numbers were taken, with a link to the
          page holding the current version.
        </p>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Corrections
        </h2>
        <p className="mt-4 text-[16px] leading-relaxed">
          Corrections are free, applied the same day, and made whether or not
          the provider asks. If a figure here is wrong, tell us and we will fix
          it rather than defend it.
        </p>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What we do not do
        </h2>
        <ul
          className="mt-4 space-y-3 text-[16px] leading-relaxed"
          style={{ color: C.muted }}
        >
          <li>
            <strong style={{ color: C.ink }}>
              We do not charge to be listed.
            </strong>{" "}
            No provider can pay to appear, to rank higher, or to have a figure
            removed.
          </li>
          <li>
            <strong style={{ color: C.ink }}>We do not give advice.</strong>{" "}
            Telling you which product suits your circumstances is a personal
            recommendation and requires a licence from the Securities and
            Exchange Commission, which we do not hold. We compare what things
            cost and what they have done.
          </li>
          <li>
            <strong style={{ color: C.ink }}>
              We do not sell advertising beside the comparisons.
            </strong>{" "}
            Articles may carry a labelled sponsor. The comparison pages, the
            matching flows and the listings carry none, and will not.
          </li>
          <li>
            <strong style={{ color: C.ink }}>We do not estimate.</strong> A
            plausible number is still a made-up one.
          </li>
        </ul>

        <section
          className="mt-12 rounded-2xl p-5 sm:p-6"
          style={{ background: C.card, border: `1px solid ${C.gold}` }}
        >
          <h2 className="text-[15px] font-bold">
            If we have something wrong about you
          </h2>
          <p
            className="mt-2 text-[14px] leading-relaxed"
            style={{ color: C.muted }}
          >
            Send the correction and the document it comes from. We will publish
            it beside your name, cited and dated, at no cost — and we would
            rather be corrected than be wrong.
          </p>
          <p className="mt-3 text-[14px] font-semibold">
            <a
              href={`mailto:${BRAND.dataEmail}`}
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              {BRAND.dataEmail}
            </a>
          </p>
        </section>

        <p className="mt-8 text-[13px]">
          <Link
            href="/"
            className="underline underline-offset-4"
            style={{ color: C.deep }}
          >
            &larr; Back to the comparisons
          </Link>
        </p>
      </div>

      <Footer />
    </main>
  );
}
