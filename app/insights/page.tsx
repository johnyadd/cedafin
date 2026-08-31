/**
 * app/insights/page.tsx — the articles.
 *
 * WHY THIS SECTION EXISTS
 * The comparison pages answer a question someone already has: what does this
 * fund cost, what does that bank charge. Articles answer questions they did
 * not know to ask — that a quarter-ounce gold coin costs more than twice what
 * a full ounce does, proportionally; that not one of twenty-four Ghanaian
 * brokers publishes a commission rate; that a share of the market can swing
 * from 20% to 79% in a month on an exchange this thin.
 *
 * Those findings came out of the data and would otherwise sit in a database
 * nobody reads. They are also, practically, the only way a site like this gets
 * read at all — nobody searches for "fund charge comparison Ghana", but people
 * do read a piece explaining why the small gold coin is the expensive one.
 *
 * SPONSORSHIP LIVES HERE AND NOWHERE ELSE
 * Articles can carry a labelled sponsor. Comparison pages, matching flows and
 * listings cannot, ever. See components/AdSlot.tsx for why.
 */

import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import { BRAND } from "@/lib/brand";
import { getArticles } from "@/lib/insights";

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
  bg: "#F2F6F9",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
};

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

export const metadata = {
  title: "Insights",
  description:
    "What the numbers show about Ghanaian savings, credit, gold and shares — " +
    "written from the same sourced data as the comparison pages.",
};

export const revalidate = 3600;

export default function InsightsPage() {
  const articles = getArticles();

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <header className="mx-auto max-w-3xl px-5 pt-6 sm:px-8">
        <Link
          href="/"
          className="text-[19px] font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: C.deep }}
        >
          {BRAND.name}
        </Link>
      </header>

      <div className="mx-auto max-w-3xl px-5 py-8 sm:px-8 sm:py-10">
        <h1
          className="text-[2rem] font-bold leading-[1.1] sm:text-[2.6rem]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What the numbers show
        </h1>
        <p
          className="mt-4 max-w-xl text-[15px] leading-relaxed"
          style={{ color: C.muted }}
        >
          Findings from the same data as the comparison pages — every figure
          traceable to a document its issuer published. Where something
          isn&rsquo;t known, these say so rather than filling the gap.
        </p>

        {articles.length === 0 ? (
          <p className="mt-10 text-[14px]" style={{ color: C.muted }}>
            Nothing published yet.
          </p>
        ) : (
          <ol className="mt-10 space-y-4">
            {articles.map((a) => (
              <li key={a.slug}>
                <Link
                  href={`/insights/${a.slug}`}
                  className="block rounded-2xl p-5 transition-colors sm:p-6"
                  style={{ background: C.card, border: `1px solid ${C.rule}` }}
                >
                  <div
                    className="flex flex-wrap items-center gap-x-3 text-[11px] font-semibold uppercase tracking-wider"
                    style={{ color: C.gold }}
                  >
                    <span>{fmtDate(a.date)}</span>
                    <span style={{ color: C.muted }}>
                      {a.readingMinutes} min read
                    </span>
                  </div>
                  <h2
                    className="mt-2 text-[19px] font-bold leading-snug sm:text-[22px]"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    {a.title}
                  </h2>
                  {a.summary && (
                    <p
                      className="mt-2 text-[14px] leading-relaxed"
                      style={{ color: C.muted }}
                    >
                      {a.summary}
                    </p>
                  )}
                  {a.tags.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {a.tags.map((t) => (
                        <span
                          key={t}
                          className="rounded-full px-3 py-1 text-[11px] font-semibold"
                          style={{ background: C.bg, color: C.muted }}
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </Link>
              </li>
            ))}
          </ol>
        )}

        {/*
          Said here rather than only beside a placement, because a reader
          deciding whether to trust this section should find the arrangement
          before the first sponsored article rather than after it.
        */}
        <section
          className="mt-14 rounded-2xl p-5 sm:p-6"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2 className="text-[15px] font-bold">How this section is paid for</h2>
          <p
            className="mt-2 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            Articles may carry a labelled sponsor. Sponsors see no copy before
            publication and have never affected a figure, a ranking or a
            comparison on this site. The comparison pages, the matching flows
            and the broker and share listings carry no advertising at all and
            never will — a banner beside a ranking would destroy the only thing
            this site has.
          </p>
          <p className="mt-3 text-[13.5px]">
            <a
              href={`mailto:${BRAND.dataEmail.replace("data@", "sales@")}`}
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              Sponsorship enquiries
            </a>
          </p>
        </section>
      </div>

      <Footer />
    </main>
  );
}
