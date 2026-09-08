import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import TbillTool, { type TbillRate } from "@/components/TbillTool";
import { getTbillRates, getLatestInflation } from "@/lib/data/funds";

/**
 * app/treasury-bill-calculator/page.tsx
 *
 * WHY THIS PAGE EXISTS
 * A search for Ghanaian Treasury bill rates returns Bank of Ghana at the top,
 * which is right — they set them. Further down sits a calculator whose
 * published rates are from the high-rate era: 25.2% against BoG's current
 * 4.75%. Somebody using it today gets an answer five times too high.
 *
 * That is the gap. Not the rate, which the central bank owns, but the
 * arithmetic on top of it — done with figures that are current.
 *
 * THE QUESTION IT ANSWERS
 * Not "what does GH₵1,000 become", which anybody can work out. The reverse: a
 * business owes GH₵15,000 in three months and has the money now. What goes
 * into the bill today? That is how the instrument is actually used, and
 * working backwards from the face value is the part people get wrong.
 *
 * WHAT IT SAYS THAT NOTHING ELSE DOES
 * The real return. At 4.80% for 91 days against 5% inflation, a Treasury bill
 * loses purchasing power — the money comes back larger and buys less. Every
 * other Ghanaian source shows the nominal rate alone.
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
  gold: "#E8A33D",
  bg: "#F2F6F9",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
};

export const metadata = {
  title: "Ghana Treasury bill calculator — what to buy for what you need",
  description:
    "Work out what a Ghanaian Treasury bill costs today to give you the amount you need on a date, using current Bank of Ghana rates — and what it earns after inflation.",
  keywords: [
    "Ghana treasury bill calculator",
    "T-bill rate Ghana",
    "treasury bill Ghana how much",
    "91 day treasury bill Ghana",
    "Ghana T-bill maturity value",
  ],
};

const FAQ: { q: string; a: string }[] = [
  {
    q: "How do Ghana Treasury bills work?",
    a: "You buy at a discount and receive the face value at maturity. Put another way, you pay less than you get back, and the difference is your return. A 91-day bill bought today pays out in 91 days with nothing in between — there is no monthly interest.",
  },
  {
    q: "How much do I need to invest to get a specific amount?",
    a: "Divide the amount you need by one plus the rate times the days over 365. At 4.80% for 91 days, GH₵15,000 at maturity costs about GH₵14,822 today. The calculator above does this — set it to 'I need an amount on a date'.",
  },
  {
    q: "What is the current Treasury bill rate in Ghana?",
    a: "Rates are set weekly at auction and published by Bank of Ghana. The calculator above shows the latest we hold for each tenor, with the date. Because they are set at auction, the rate you get is the one at the auction you buy into, not today's.",
  },
  {
    q: "Are Ghana Treasury bills taxed?",
    a: "Ecobank state that no taxes are payable on Treasury bills bought through their TBill4All platform. Tax treatment can depend on how you buy and who you are, so ask your provider rather than assuming.",
  },
  {
    q: "Do Treasury bills beat inflation in Ghana?",
    a: "Not at the short end, currently. The 91-day rate is close to the inflation rate, which means the money comes back larger and buys about the same. Longer tenors pay more and are further ahead. The calculator shows the real return for whichever tenor you pick.",
  },
  {
    q: "What is the minimum to buy a Treasury bill in Ghana?",
    a: "It depends where you buy. Ecobank's TBill4All takes GH₵5 through MTN Mobile Money with no bank account. Buying through a bank branch typically requires several hundred cedis or more, and some charge a processing fee on top.",
  },
];

export const revalidate = 3600;

export default async function TreasuryBillCalculatorPage() {
  const [rates, inflation] = await Promise.all([
    getTbillRates(),
    getLatestInflation(),
  ]);

  const tenors: TbillRate[] = rates.map((r) => ({
    days: r.days,
    label: `${r.days} days`,
    ratePct: r.ratePct,
    asOf: r.asOf,
  }));

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
          Ghana Treasury bill calculator
        </h1>
        <p
          className="mt-3 max-w-2xl text-[14.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          What to buy today for the amount you need on a date — or what a sum
          you have would return. Using the latest rates we hold, and showing
          what the money will actually buy after inflation.
        </p>

        <div className="mt-6">
          {tenors.length ? (
            <TbillTool rates={tenors} inflationPct={inflation} />
          ) : (
            <p className="text-[15px]" style={{ color: C.muted }}>
              We hold no current Treasury bill rates. Bank of Ghana publishes
              them weekly.
            </p>
          )}
        </div>

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
          <h2 className="text-[14px] font-bold">Where the rates come from</h2>
          <p
            className="mt-2 text-[13px] leading-relaxed"
            style={{ color: C.muted }}
          >
            Bank of Ghana publishes Treasury bill results after each weekly
            auction. We take the interest rate rather than the discount rate,
            because the interest rate is the yield on what you actually pay —
            using the discount rate would understate what a buyer earns. Every
            figure here carries the date it was true.
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
          Buying with as little as GH&#8373;5 is possible through mobile money.{" "}
          <Link
            href="/compare/government_security-GHS"
            className="font-semibold underline underline-offset-4"
            style={{ color: C.deep }}
          >
            Compare the ways in
          </Link>
          .
        </p>
      </div>

      <Footer />
    </main>
  );
}
