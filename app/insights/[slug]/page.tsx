/**
 * app/insights/[slug]/page.tsx — one article.
 *
 * WHY THE SOURCES SIT AT THE FOOT OF EVERY PIECE
 * The comparison pages date and cite every figure. An article that made claims
 * without saying where they came from would be held to a lower standard than
 * the tables it draws on, which is the wrong way round — prose is easier to be
 * loose in, so it needs the discipline more.
 *
 * WHERE THE SPONSOR SLOT GOES
 * One placement, after the article, before the sources. Not in the middle of
 * the argument and not above the headline. A reader should finish the piece
 * before meeting a sponsor, and the sources should be the last thing on the
 * page — they are what the article rests on.
 */

import Link from "next/link";
import { notFound } from "next/navigation";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import AdSlot from "@/components/AdSlot";
import Share from "@/components/Share";
import Subscribe from "@/components/Subscribe";
import Footer from "@/components/Footer";
import Markdown from "@/components/Markdown";
import { BRAND } from "@/lib/brand";
import { getArticle, getArticleSlugs, getArticles } from "@/lib/insights";

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

export function generateStaticParams() {
  return getArticleSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const a = getArticle(slug);
  if (!a) return { title: "Not found" };
  return { title: a.title, description: a.summary };
}

export const revalidate = 3600;

export default async function ArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = getArticle(slug);
  if (!article) notFound();

  const others = getArticles()
    .filter((a) => a.slug !== slug)
    .slice(0, 3);

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <header className="mx-auto max-w-2xl px-5 pt-6 sm:px-8">
        <Link
          href="/"
          className="text-[19px] font-bold tracking-tight"
          style={{ fontFamily: "var(--font-display)", color: C.deep }}
        >
          {BRAND.name}
        </Link>
      </header>

      <article className="mx-auto max-w-2xl px-5 py-8 sm:px-8 sm:py-10">
        <p className="text-[13px]">
          <Link
            href="/insights"
            className="underline underline-offset-4"
            style={{ color: C.deep }}
          >
            ← All insights
          </Link>
        </p>

        <div
          className="mt-6 flex flex-wrap items-center gap-x-3 text-[11px] font-semibold uppercase tracking-wider"
          style={{ color: C.gold }}
        >
          <span>{fmtDate(article.date)}</span>
          <span style={{ color: C.muted }}>
            {article.readingMinutes} min read
          </span>
        </div>

        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.12] sm:text-[2.5rem]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {article.title}
        </h1>

        {article.summary && (
          <p
            className="mt-4 text-[16px] leading-relaxed"
            style={{ color: C.muted }}
          >
            {article.summary}
          </p>
        )}

        <div
          className="mt-8 border-t pt-6"
          style={{ borderColor: C.rule }}
        >
          <Markdown body={article.body} />
        </div>

        {/*
          The subscribe box sits AFTER the article, not before it and not in a
          pop-up. Someone who has read to the end has demonstrated interest;
          someone interrupted at the second paragraph has demonstrated nothing
          except that they were reading. Conversion bought by interrupting is
          conversion from people who will unsubscribe.
        */}
        <div className="mt-10">
          <Subscribe source={`insights/${slug}`} />
        </div>

        <Share title={article.title} slug={slug} />

        <AdSlot placement={`article-${slug}`} />

        {article.sources.length > 0 && (
          <section
            className="mt-10 rounded-2xl p-5"
            style={{ background: C.card, border: `1px solid ${C.rule}` }}
          >
            <h2
              className="text-[11px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: C.gold }}
            >
              Where these figures come from
            </h2>
            <ul
              className="mt-3 space-y-1.5 text-[12.5px] leading-relaxed"
              style={{ color: C.muted }}
            >
              {article.sources.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
            <p className="mt-4 text-[12.5px]" style={{ color: C.muted }}>
              If a figure here is wrong or out of date,{" "}
              <a
                href={`mailto:${BRAND.dataEmail}`}
                className="underline underline-offset-4"
                style={{ color: C.deep }}
              >
                tell us
              </a>{" "}
              and we will correct it, cited and dated.
            </p>
          </section>
        )}

        {others.length > 0 && (
          <section className="mt-12">
            <h2
              className="text-[11px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: C.gold }}
            >
              More
            </h2>
            <ul className="mt-3 space-y-2">
              {others.map((a) => (
                <li key={a.slug}>
                  <Link
                    href={`/insights/${a.slug}`}
                    className="text-[14px] font-semibold underline underline-offset-4"
                    style={{ color: C.deep }}
                  >
                    {a.title}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}
      </article>

      <Footer />
    </main>
  );
}
