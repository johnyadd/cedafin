import fs from "node:fs";
import path from "node:path";

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import { BRAND } from "@/lib/brand";

/**
 * app/the-archive/page.tsx
 *
 * WHY THIS PAGE EXISTS
 * The strongest thing on this site is the one a visitor could not see. A
 * hundred and eighty-five source documents: eighteen months of exchange
 * reports, factsheets going back to January 2024, daily circulars, and three
 * Bank of Ghana returns that the Bank itself no longer publishes.
 *
 * Nothing referenced any of it. The site looked like every other comparison
 * site — figures on a page, take it or leave it.
 *
 * THE FRAMING, WHICH MATTERS MORE THAN THE CONTENT
 * This is not "look how much data we hold". A boast invites doubt, and a
 * number of documents means nothing to a reader.
 *
 * It is a service, and the service is only legible once you know what the
 * institutions do. Bank of Ghana publishes an APR return every month and
 * takes down the previous one. Fund managers replace a factsheet rather than
 * versioning it. The Exchange posts this month's report.
 *
 * So: a borrower cannot see whether lending costs are improving. A saver
 * cannot prove a fee went up. Nobody can answer "when did that change" —
 * unless somebody kept the documents.
 *
 * We kept them. That is the whole page.
 *
 * WHY IT READS THE FILESYSTEM
 * Counting the files at build time rather than hard-coding them means the page
 * cannot claim an archive that has stopped growing. If a fetcher breaks and
 * the gold circulars stop arriving, this page says so without anyone noticing
 * first.
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
  title: "The archive — the documents Ghana's institutions don't keep",
  description:
    "Every figure on this site comes from a document, and we keep the document. Bank of Ghana removes last month's return; fund managers replace factsheets. We hold the back numbers, which is why questions about change can be answered here.",
};

/**
 * What each series is, and — the part that matters — what the publisher does
 * with its own back numbers.
 */
const SERIES: {
  dir: string;
  label: string;
  publisher: string;
  theyKeep: string;
  whyItMatters: string;
  irreplaceable?: boolean;
}[] = [
  {
    dir: "apr",
    label: "Bank of Ghana lending rate returns",
    publisher: "Bank of Ghana",
    theyKeep:
      "The current notice only. We checked eight earlier months and found none.",
    whyItMatters:
      "Every bank's advertised rate and its all-in cost, monthly. Without the back numbers nobody can say whether borrowing is getting cheaper — which is a question we were asked by a journalist and could only answer because we had kept them.",
    irreplaceable: true,
  },
  {
    dir: "gse",
    label: "Ghana Stock Exchange monthly reports",
    publisher: "Ghana Stock Exchange",
    theyKeep: "An archive back to 2017, which is better than most.",
    whyItMatters:
      "Share prices and every broker's share of trading. The eighteen-month series behind our brokers page is assembled from these, and rebuilding it would take eighteen months if the Exchange ever stopped.",
  },
  {
    dir: "factsheets",
    label: "Fund factsheets",
    publisher: "fund managers",
    theyKeep:
      "The current one. A factsheet is replaced, not versioned — last month's is simply gone.",
    whyItMatters:
      "This is how we can say a fund cut its charge from 2.65% to 2.25% on a particular date. The manager's own site shows only the figure that is true today, so the change is provable only from documents somebody kept.",
    irreplaceable: true,
  },
  {
    dir: "goldcoin",
    label: "Gold coin price circulars",
    publisher: "Bank of Ghana",
    theyKeep: "The current day's.",
    whyItMatters:
      "Issued every business day. A daily series exists here and nowhere else we have found.",
    irreplaceable: true,
  },
  {
    dir: "tbills",
    label: "Treasury bill auction results",
    publisher: "Bank of Ghana",
    theyKeep: "Recent tenders.",
    whyItMatters:
      "What the government paid to borrow, weekly. The benchmark every other Ghanaian return is measured against.",
  },
  {
    dir: "faam",
    label: "Fund manager reports",
    publisher: "fund managers",
    theyKeep: "The current one.",
    whyItMatters:
      "Monthly performance and holdings for funds whose managers publish no history.",
  },
  {
    dir: "sec",
    label: "Securities and Exchange Commission registers",
    publisher: "Securities and Exchange Commission",
    theyKeep: "Today's register. There is no published history.",
    whyItMatters:
      "Who was licensed, and when. Registers are edited silently — a firm appears, a name changes, an entry goes. When somebody asks when a firm was struck off, the only honest answer available today is that the register does not say. We started keeping it in September 2026, so from a month from now there will be something to compare.",
    irreplaceable: true,
  },
];

/** Count files on disk at build time, so the page cannot overstate. */
function countFiles(dir: string): { files: number; bytes: number } {
  const root = path.join(process.cwd(), "data", dir);
  let files = 0;
  let bytes = 0;
  const walk = (d: string) => {
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(d, { withFileTypes: true });
    } catch {
      return;
    }
    for (const e of entries) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) walk(p);
      else {
        files += 1;
        try {
          bytes += fs.statSync(p).size;
        } catch {
          /* counted without its size */
        }
      }
    }
  };
  walk(root);
  return { files, bytes };
}

export const revalidate = 3600;

export default function TheArchivePage() {
  const counted = SERIES.map((s) => ({ ...s, ...countFiles(s.dir) })).filter(
    (s) => s.files > 0,
  );
  const totalFiles = counted.reduce((n, s) => n + s.files, 0);
  const totalMb = counted.reduce((n, s) => n + s.bytes, 0) / 1_048_576;

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
          Why this is not a comparison site
        </p>
        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.1] sm:text-[2.4rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.02em",
          }}
        >
          We keep the documents
        </h1>
        <p
          className="mt-5 text-[16.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          Every figure on this site comes from a document somebody published.
          That is ordinary enough. What is less ordinary is that we still have
          the document — and in several cases nobody else does, including the
          institution that issued it.
        </p>

        <div
          className="mt-6 rounded-2xl p-5"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <p className="text-[15px] leading-relaxed">
            <strong>Bank of Ghana publishes a lending rate return every
            month and removes the previous one.</strong>{" "}
            Fund managers replace a factsheet rather than versioning it. The
            Exchange posts this month&rsquo;s report. Registers show today.
          </p>
          <p
            className="mt-3 text-[15px] leading-relaxed"
            style={{ color: C.muted }}
          >
            So a borrower cannot see whether credit is getting cheaper. A saver
            cannot prove a charge went up. Nobody can answer{" "}
            <em>when did that change</em> — unless somebody kept the back
            numbers.
          </p>
          <p className="mt-3 text-[15px] font-semibold">
            We keep them. {totalFiles} documents, {totalMb.toFixed(0)} MB, and
            growing every week without anybody remembering to.
          </p>
        </div>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What is held
        </h2>
        <p className="mt-2 text-[14px]" style={{ color: C.muted }}>
          Counted from the files themselves each time this page is built, so it
          cannot claim an archive that has stopped growing.
        </p>

        <div className="mt-5 space-y-3">
          {counted.map((s) => (
            <section
              key={s.dir}
              className="overflow-hidden rounded-2xl"
              style={{
                background: C.card,
                border: `1px solid ${s.irreplaceable ? C.gold : C.rule}`,
              }}
            >
              <div className="flex">
                <span
                  className="w-1 shrink-0"
                  style={{ background: s.irreplaceable ? C.gold : C.rule }}
                  aria-hidden="true"
                />
                <div className="flex-1 p-5">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <h3 className="text-[14.5px] font-bold">{s.label}</h3>
                    <span className="text-[13px] font-semibold tabular-nums" style={{ color: C.muted }}>
                      {s.files} document{s.files === 1 ? "" : "s"}
                    </span>
                  </div>
                  <p className="mt-1.5 text-[12.5px]" style={{ color: C.muted }}>
                    Published by {s.publisher}. They keep: {s.theyKeep}
                  </p>
                  <p className="mt-2.5 text-[13.5px] leading-relaxed">
                    {s.whyItMatters}
                  </p>
                  {s.irreplaceable && (
                    <p
                      className="mt-2.5 text-[12.5px] font-semibold"
                      style={{ color: C.clay }}
                    >
                      Some of these cannot be obtained anywhere else, at any
                      price, by anybody.
                    </p>
                  )}
                </div>
              </div>
            </section>
          ))}
        </div>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What this lets the site answer
        </h2>
        <div className="mt-4 space-y-4 text-[15.5px] leading-relaxed">
          <p>
            <strong>Whether bank fees are rising or falling.</strong> Across
            four returns spanning twenty months, the gap between the advertised
            rate and the all-in cost narrowed by 49% for corporate borrowers and
            16% for small businesses. Three of those four returns are no longer
            published by the Bank.{" "}
            <Link
              href="/insights/bank-fees-falling-not-equally"
              className="font-semibold underline underline-offset-4"
              style={{ color: C.deep }}
            >
              The analysis &rarr;
            </Link>
          </p>
          <p>
            <strong>When a fund changed its charge.</strong> Stanbic Cash Trust
            moved from 2.65% to 2.25% on 1 June 2026. Provable only because both
            factsheets survive; their own site shows the current one.
          </p>
          <p>
            <strong>How concentrated the stock market actually is.</strong> One
            broker averages 54% of value traded across eighteen months — and
            swings between 20% and 79% month to month, which is a fact about how
            thin the market is rather than about any firm.{" "}
            <Link
              href="/brokers"
              className="font-semibold underline underline-offset-4"
              style={{ color: C.deep }}
            >
              The series &rarr;
            </Link>
          </p>
        </div>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          The gaps, which we also record
        </h2>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          Seventeen months of Bank of Ghana returns are missing, between
          September 2024 and May 2026. They were published, and they were taken
          down before we started collecting. We cannot get them, and we say so
          rather than presenting the series as complete.
        </p>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          A series with a hole in it looks whole until somebody computes across
          it. The gaps are checked automatically and reported, for the same
          reason every figure here carries a date.
        </p>

        <div
          className="mt-8 rounded-2xl p-5"
          style={{ background: "#FFF8EC", border: `1px solid ${C.gold}` }}
        >
          <p className="text-[14px] font-bold">
            If you need something from it
          </p>
          <p
            className="mt-2 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            Journalists, researchers, regulators and anybody else: ask, and we
            will send the underlying document. No charge, no permission needed,
            no credit required. An archive nobody can reach is only half an
            archive.
          </p>
          <p className="mt-2.5 text-[13px]">
            <a
              href={`mailto:${BRAND.dataEmail}`}
              className="font-semibold underline underline-offset-4"
              style={{ color: C.deep }}
            >
              {BRAND.dataEmail}
            </a>
            {" · "}
            <Link
              href="/for-journalists"
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              For journalists
            </Link>
            {" · "}
            <Link
              href="/methodology"
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              How we source every figure
            </Link>
          </p>
        </div>

        <p className="mt-8 text-[12.5px] leading-relaxed" style={{ color: C.muted }}>
          {BRAND.legalStatus} These are public documents, published by the
          institutions named and kept as issued. We hold them because the
          questions readers ask are about change, and change cannot be shown
          from a single document.
        </p>
      </div>

      <Footer />
    </main>
  );
}
