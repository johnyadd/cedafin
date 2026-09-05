import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import InflationTool from "@/components/InflationTool";
import { getCpiIndex } from "@/lib/data/funds";

/**
 * app/inflation-calculator/page.tsx
 *
 * WHY A SEPARATE PAGE RATHER THAN A LINE IN THE RETURNS CALCULATOR
 * They answer different questions. The returns calculator asks what an
 * investment earned after inflation; this asks what money from one year is
 * worth in another. A visitor searching "Ghana inflation calculator" wants the
 * second, and a line buried inside another tool will never rank for it.
 *
 * WHY IT IS WORTH BUILDING AT ALL
 * Dozens of inflation calculators exist and almost all of them are American.
 * The ones covering other countries use World Bank annual data at a coarse
 * grain and rarely name the country in the title. A Ghanaian one, with sixty
 * years of local index, is a thing that does not currently exist.
 *
 * THE REDENOMINATION
 * Ghana dropped four zeroes in July 2007 — GH₵1 replaced ¢10,000. The index is
 * continuous across it because it measures prices rather than currency units,
 * so the arithmetic is right. But an answer spanning 2007 will look wrong to
 * anyone who remembers the old notes, so the tool says so rather than leaving
 * them to wonder.
 *
 * SEO
 * The title is what people type. The FAQ block carries structured data whose
 * answers are visible on the page, generated from the same array so they
 * cannot drift apart.
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
  bg: "#F2F6F9",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
};

export const metadata = {
  title: "Ghana inflation calculator — what your cedis were worth",
  description:
    "Work out what an amount of money from any year since 1964 is worth in cedis today, using Ghana's own consumer price index. Free, no sign-up, and every figure sourced.",
  keywords: [
    "Ghana inflation calculator",
    "cedi purchasing power",
    "Ghana consumer price index",
    "value of money Ghana",
    "GHS inflation",
  ],
};

const FAQ: { q: string; a: string }[] = [
  {
    q: "How do you calculate inflation in Ghana?",
    a: "Divide the consumer price index of the later year by the index of the earlier year, and multiply by the amount. Ghana's index is published with 2010 as the base year, so a reading of 855.8 for 2025 means prices are roughly 8.6 times their 2010 level. This calculator does that arithmetic for any two years from 1964 onwards.",
  },
  {
    q: "What is Ghana's inflation rate now?",
    a: "Year-on-year inflation was 5.0% in August 2026, according to the Ghana Statistical Service. It has fallen a long way — it was 13.7% in June 2025 and reached 3.2% in March 2026, the lowest in about three decades, before ticking back up.",
  },
  {
    q: "Why does an old amount look so large in today's cedis?",
    a: "Because Ghana redenominated the currency in July 2007, dropping four zeroes: GH₵1 replaced ¢10,000. The price index is continuous across that change because it measures prices rather than currency units, so the arithmetic is correct — but an amount from before 2007 was quoted in old cedis, and comparing it to today needs that in mind.",
  },
  {
    q: "Where does this data come from?",
    a: "The annual index is Ghana's consumer price index as published by the World Bank, sourced from the IMF's International Financial Statistics, which takes it from the Ghana Statistical Service. Monthly inflation rates come from GSS releases directly.",
  },
  {
    q: "Does inflation mean my savings are losing value?",
    a: "If your interest rate is below inflation, yes. In August 2026 the 91-day Ghanaian Treasury bill paid 5.08% and inflation was 5.0%, so a saver in the shortest bill was roughly standing still. The 364-day bill at 11.59% was comfortably ahead.",
  },
];

export const revalidate = 3600;

export default async function InflationCalculatorPage() {
  const index = await getCpiIndex();

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

      <div className="mx-auto max-w-3xl px-5 py-8 sm:px-8 sm:py-10">
        <h1
          className="text-[1.7rem] font-bold leading-[1.12] sm:text-[2.1rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.015em",
          }}
        >
          Ghana inflation calculator
        </h1>
        <p
          className="mt-3 max-w-2xl text-[14.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          What an amount of money from any year since 1964 is worth in cedis
          today, using Ghana&rsquo;s own consumer price index.
        </p>

        <div className="mt-6">
          <InflationTool index={index} />
        </div>

        {/* The questions people actually type, answered from the data above. */}
        <section className="mt-10">
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

        <section
          className="mt-8 rounded-2xl p-5"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2 className="text-[14px] font-bold">Where these figures come from</h2>
          <p
            className="mt-2 text-[13px] leading-relaxed"
            style={{ color: C.muted }}
          >
            The annual index is Ghana&rsquo;s consumer price index published by
            the World Bank, sourced from the IMF&rsquo;s International Financial
            Statistics and originally from the Ghana Statistical Service. It
            runs from 1964 to 2025 with 2010 as the base year. Monthly inflation
            rates elsewhere on this site come from GSS releases directly.
          </p>
          <p className="mt-3 text-[13px]">
            <Link
              href="/methodology"
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              How we source every figure &rarr;
            </Link>
          </p>
        </section>

        <p className="mt-6 text-[13px]" style={{ color: C.muted }}>
          Working out what an <em>investment</em> earned after inflation is a
          different question.{" "}
          <Link
            href="/calculator"
            className="font-semibold underline underline-offset-4"
            style={{ color: C.deep }}
          >
            The returns calculator does that
          </Link>
          .
        </p>
      </div>

      <Footer />
    </main>
  );
}
