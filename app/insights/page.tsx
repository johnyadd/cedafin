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

/**
 * Tags carry their subject's colour, so someone scanning the list sees what a
 * piece is about before reading a word of it. Anything unlisted falls back to
 * grey rather than getting an arbitrary colour — a tag that looks meaningful
 * and is not would be worse than a plain one.
 */
const TAG_COLOURS: Record<string, string> = {
  gold: "#B8860B",
  brokers: "#0B4F6C",
  shares: "#0B4F6C",
  GSE: "#0B4F6C",
  lending: "#8A4B1F",
  banks: "#8A4B1F",
  SME: "#8A4B1F",
  costs: "#C0492B",
  returns: "#0E8F62",
  "Bank of Ghana": "#5F6E78",
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
        <section
          className="overflow-hidden rounded-3xl p-7 text-white sm:p-10"
          style={{
            background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 72%)`,
          }}
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-80">
            Insights
          </p>
          <h1
            className="mt-3 text-[2.2rem] font-bold leading-[1.08] sm:text-[3rem]"
            style={{
              fontFamily: "var(--font-display)",
              letterSpacing: "-0.02em",
            }}
          >
            What the numbers
            <br />
            show
          </h1>
          <p className="mt-5 max-w-xl text-[15px] leading-relaxed opacity-90">
            Findings from the same data as the comparison pages — every figure
            traceable to a document its issuer published. Where something
            isn&rsquo;t known, these say so rather than filling the gap.
          </p>
        </section>

        {articles.length === 0 ? (
          <p className="mt-10 text-[14px]" style={{ color: C.muted }}>
            Nothing published yet.
          </p>
        ) : (
          <ol className="mt-10 space-y-5">
            {articles.map((a) => (
              <li key={a.slug}>
                <Link
                  href={`/insights/${a.slug}`}
                  className="group block overflow-hidden rounded-2xl transition-shadow hover:shadow-lg"
                  style={{ background: C.card, border: `1px solid ${C.rule}` }}
                >
                  {/* A gold bar down the left edge — the only ornament, and it
                      marks the card as one thing rather than a block of text. */}
                  <div className="flex">
                    <div
                      className="w-1 shrink-0"
                      style={{ background: C.gold }}
                    />
                    <div className="flex-1 p-5 sm:p-6">
                      <div className="flex flex-wrap items-center gap-x-2.5 text-[11px] font-semibold uppercase tracking-[0.12em]">
                        <span style={{ color: C.gold }}>{fmtDate(a.date)}</span>
                        <span aria-hidden="true" style={{ color: C.rule }}>
                          ·
                        </span>
                        <span style={{ color: C.muted }}>
                          {a.readingMinutes} min read
                        </span>
                      </div>

                      <h2
                        className="mt-2.5 text-[21px] font-bold leading-[1.2] sm:text-[25px]"
                        style={{
                          fontFamily: "var(--font-display)",
                          letterSpacing: "-0.01em",
                        }}
                      >
                        {a.title}
                      </h2>

                      {a.summary && (
                        <p
                          className="mt-2.5 text-[14.5px] leading-relaxed"
                          style={{ color: C.muted, maxWidth: "60ch" }}
                        >
                          {a.summary}
                        </p>
                      )}

                      {a.tags.length > 0 && (
                        <div className="mt-4 flex flex-wrap items-center gap-2">
                          {a.tags.map((t) => {
                            const colour = TAG_COLOURS[t] ?? C.muted;
                            return (
                              <span
                                key={t}
                                className="rounded-full px-3 py-1 text-[11px] font-bold"
                                style={{
                                  background: `${colour}15`,
                                  color: colour,
                                  border: `1px solid ${colour}30`,
                                }}
                              >
                                {t}
                              </span>
                            );
                          })}
                          <span
                            className="ml-auto text-[13px] font-bold opacity-0 transition-opacity group-hover:opacity-100"
                            style={{ color: C.deep }}
                          >
                            Read →
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
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
