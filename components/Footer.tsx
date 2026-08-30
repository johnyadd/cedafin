/**
 * components/Footer.tsx — the same ending on every page.
 *
 * WHY A SITE MAP AND NOT THREE LINKS
 * The matching flows sat unreachable for a day because nothing linked to them,
 * and the brokers and shares pages nearly repeated it. Internal linking on
 * this site has been an afterthought each time a page was added, so the footer
 * lists everything — nine page types — and any future page that is missing
 * from it will be obvious.
 *
 * WHY THE SOURCES ARE NAMED
 * Every figure on this site comes from a document its issuer published: Bank
 * of Ghana's circulars, the exchange's monthly reports, the SEC's registers,
 * fund factsheets. Naming them in the footer is not decoration — it is the
 * claim the whole site rests on, and a reader who wants to check a number
 * should be able to see where to start without hunting.
 *
 * WHY THE LEGAL LINE IS HERE RATHER THAN ONLY ON EACH PAGE
 * Not licensed by the SEC, no advice, no client money, no transactions. That
 * belongs everywhere someone might land, and pages keep their own specific
 * disclosures on top of it rather than instead of it.
 */

import Link from "next/link";

import { BRAND } from "@/lib/brand";

// Inverted for a dark footer. Gold headings carry through from the rest of
// the site; the blue is lightened because #0B4F6C on near-black fails every
// contrast threshold — a link nobody can read is not a link.
const C = {
  ink: "#F2F6F9",
  deep: "#5FB6DE",
  gold: "#E8A33D",
  rule: "#2A3138",
  muted: "#98A6B0",
  bg: "#0C1216",
};

const SECTIONS: { heading: string; links: [string, string][] }[] = [
  {
    heading: "Investing",
    links: [
      ["/funds", "Every fund"],
      ["/match", "Find what fits you"],
      ["/compare/money_market-GHS", "Money market funds"],
      ["/compare/fixed_income-GHS", "Fixed income funds"],
      ["/compare/government_security-GHS", "Treasury bills"],
    ],
  },
  {
    heading: "Shares and gold",
    links: [
      ["/shares", "Listed shares"],
      ["/brokers", "Stockbrokers"],
      ["/compare/commodity-GHS", "Gold"],
      ["/compare/equity-GHS", "Compare shares"],
    ],
  },
  {
    heading: "Borrowing",
    links: [
      ["/funding", "Compare business credit"],
      ["/funding/match", "Find funding that fits"],
    ],
  },
];

const SOURCES = [
  "Bank of Ghana — Treasury bill tenders, APR reports, Ghana Gold Coin pricing",
  "Ghana Stock Exchange — monthly market reports",
  "Securities and Exchange Commission — licensee registers",
  "Fund managers — published factsheets",
];

export default function Footer() {
  return (
    <footer
      className="mt-16 border-t"
      style={{ borderColor: C.rule, background: C.bg }}
    >
      <div className="mx-auto max-w-5xl px-5 py-10 sm:px-8 sm:py-12">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <Link
              href="/"
              className="text-[18px] font-bold tracking-tight"
              style={{ color: C.deep }}
            >
              {BRAND.name}
            </Link>
            <p
              className="mt-3 max-w-xs text-[12.5px] leading-relaxed"
              style={{ color: C.muted }}
            >
              What Ghanaian savings and credit actually cost, from the documents
              providers publish themselves. Every figure is dated and sourced.
            </p>
            {/*
              Labelled rather than listed. Five bare addresses tell a visitor
              nothing about which to use, and a fund manager wanting to
              correct a figure should not have to guess between sales and
              enquiries — corrections matter most here, so that one is first.
            */}
            <h2
              className="mt-6 text-[11px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: C.gold }}
            >
              Contact
            </h2>
            <ul className="mt-3 space-y-1.5 text-[12.5px]">
              {(
                [
                  ["data", "Corrections and figures"],
                  ["support", "Something wrong with the site"],
                  ["enquiries", "General questions"],
                  ["sales", "Commercial"],
                  ["hello", "Anything else"],
                ] as [string, string][]
              ).map(([box, purpose]) => (
                <li key={box}>
                  <a
                    href={`mailto:${box}@cedafin.com`}
                    className="underline underline-offset-4"
                    style={{ color: C.deep }}
                  >
                    {box}@cedafin.com
                  </a>{" "}
                  <span style={{ color: C.muted }}>— {purpose}</span>
                </li>
              ))}
            </ul>
          </div>

          {SECTIONS.map((s) => (
            <div key={s.heading}>
              <h2
                className="text-[11px] font-semibold uppercase tracking-[0.14em]"
                style={{ color: C.gold }}
              >
                {s.heading}
              </h2>
              <ul className="mt-3 space-y-1.5">
                {s.links.map(([href, label]) => (
                  <li key={href}>
                    <Link
                      href={href}
                      className="text-[13px] hover:underline hover:underline-offset-4"
                      style={{ color: C.ink }}
                    >
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div
          className="mt-10 border-t pt-6"
          style={{ borderColor: C.rule }}
        >
          <h2
            className="text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: C.gold }}
          >
            Where the figures come from
          </h2>
          <ul
            className="mt-2 space-y-1 text-[12px] leading-relaxed"
            style={{ color: C.muted }}
          >
            {SOURCES.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>

          {/*
            The ask, in the one place it appears on every page. Most of what is
            missing from this site is missing because nobody publishes it —
            brokerage rates, fund holdings, deposit terms. Providers reading
            their own page should find the invitation without looking for it.
          */}
          <p
            className="mt-5 max-w-2xl text-[12.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            <strong style={{ color: C.ink }}>
              If we have your figures wrong, or you publish something we have
              missed:
            </strong>{" "}
            send it and we will correct the page, cited and dated. We would
            rather be corrected than be wrong.
          </p>

          <p
            className="mt-5 text-[11px] leading-relaxed"
            style={{ color: C.muted }}
          >
            {BRAND.legalStatus}
          </p>
          <p className="mt-2 text-[11px]" style={{ color: C.muted }}>
            © {new Date().getFullYear()} {BRAND.name}
          </p>
        </div>
      </div>
    </footer>
  );
}
