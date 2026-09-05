import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import BorrowingTool, { type LoanOption } from "@/components/BorrowingTool";
import Footer from "@/components/Footer";
import { getLending } from "@/lib/data/funds";

/**
 * app/loan-calculator/page.tsx
 *
 * WHY THE BORROW SIDE GETS ITS OWN TOOL
 * The invest side has had a calculator for a while. The borrow side has a
 * comparison of 22 banks and a matching flow, and nothing that turns a rate
 * into a repayment — which is the number a business owner is actually trying
 * to work out.
 *
 * WHY IT COMPARES AGAINST THE MARKET
 * Most loan calculators tell you the monthly payment and stop. This one sets
 * it against the cheapest and dearest APR reported to Bank of Ghana, because
 * "GH₵9,926 a month" means nothing until you know the same loan costs
 * GH₵8,840 elsewhere.
 *
 * SEO
 * "Loan calculator Ghana" is a searched phrase. The FAQ block carries
 * structured data whose answers are visible on the page.
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
  brown: "#8A4B1F",
};

export const metadata = {
  title: "Loan calculator Ghana — what a business loan really costs",
  description:
    "Work out the monthly repayment and total cost of a Ghanaian business or personal loan, and compare it against what 22 banks actually charge. Uses Bank of Ghana's own APR data.",
  keywords: [
    "loan calculator Ghana",
    "business loan Ghana",
    "SME loan rates Ghana",
    "APR Ghana banks",
    "loan repayment calculator cedis",
  ],
};

const FAQ: { q: string; a: string }[] = [
  {
    q: "What is a good interest rate for a business loan in Ghana?",
    a: "For a one-year SME loan reported to Bank of Ghana in May 2026, the cheapest of 22 banks was 11.03% APR and the dearest 33.58%. Anything near the lower end is competitive. The important thing is to compare on APR rather than the advertised interest rate, because the APR includes the fees.",
  },
  {
    q: "What is the difference between the interest rate and the APR?",
    a: "The interest rate is one component. The annual percentage rate includes arrangement fees, commitment fees, processing charges and insurance, expressed as a single annual figure. One Ghanaian bank reports a minimum of 13.70% and a maximum of 23.42% on the same product — nearly ten percentage points of that range is fees.",
  },
  {
    q: "How much does a GH₵100,000 business loan cost in Ghana?",
    a: "Over one year at the cheapest reported APR of 11.03%, about GH₵8,840 a month and roughly GH₵106,000 in total. At the dearest reported rate of 33.58%, about GH₵9,926 a month and GH₵119,000 in total — around GH₵13,000 more for the same money over the same term.",
  },
  {
    q: "Does inflation make a loan cheaper?",
    a: "In real terms, yes. You repay in cedis worth less than the ones you borrowed. At 5% inflation, an 11.03% loan costs about 5.7% in real terms. That is not a reason to borrow, but it is part of the true cost and it is rarely stated.",
  },
  {
    q: "Which Ghanaian bank has the lowest loan rates?",
    a: "On the figures banks reported to Bank of Ghana for May 2026, Standard Chartered had the lowest APR for one-year SME credit at 11.03%. Rates differ by product, term and borrower, so the reported average is where to start asking rather than what you will be offered.",
  },
];

export const revalidate = 3600;

export default async function LoanCalculatorPage() {
  /*
    Every bank, every credit type, every term — so the tool can name the
    lender rather than quoting a rate from nowhere.

    A first version defaulted to 18.00% because it looked typical. It was not
    any bank's rate and was not sourced, which is exactly the thing this site
    criticises elsewhere.
  */
  const rows = await getLending();
  const options: LoanOption[] = rows
    .filter((r) => r.aprPct !== null)
    .map((r) => ({
      bank: r.provider.name,
      category: r.category,
      tenorYears: r.tenorYears,
      aprPct: r.aprPct as number,
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

      <div className="mx-auto max-w-4xl px-5 py-8 sm:px-8">
        <h1
          className="text-[1.7rem] font-bold leading-[1.12] sm:text-[2.1rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.015em",
          }}
        >
          What a Ghanaian business loan really costs
        </h1>
        <p
          className="mt-3 max-w-2xl text-[14.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          The monthly repayment, the total, and how it compares with what 22
          banks actually charge — from Bank of Ghana&rsquo;s own APR returns.
        </p>

        <div className="mt-6">
          <BorrowingTool options={options} />
        </div>

        <section className="mt-10">
          <h2
            className="text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: C.gold }}
          >
            Questions people ask
          </h2>
          <div className="mt-3 grid gap-2.5 sm:grid-cols-2">
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
                      style={{ color: C.brown }}
                      aria-hidden="true"
                    >
                      &#9656;
                    </span>
                    <span>{q}</span>
                  </span>
                </summary>
                <p
                  className="mt-2.5 pl-5 text-[12.5px] leading-relaxed"
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
          <h2 className="text-[14px] font-bold">What this cannot tell you</h2>
          <ul
            className="mt-3 space-y-2.5 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            <li>
              <strong style={{ color: C.ink }}>
                What you will actually be offered.
              </strong>{" "}
              Bank of Ghana&rsquo;s figures are averages across each
              bank&rsquo;s whole book. Your rate depends on your trading
              history, security and accounts.
            </li>
            <li>
              <strong style={{ color: C.ink }}>Whether you will qualify.</strong>{" "}
              For most small Ghanaian businesses access matters more than rate,
              and this says nothing about it.
            </li>
            <li>
              <strong style={{ color: C.ink }}>
                Anyone but banks.
              </strong>{" "}
              Microfinance institutions, savings and loans companies and digital
              lenders are not in the APR report — and they are where businesses
              refused by banks actually borrow.
            </li>
          </ul>
          <p className="mt-4 text-[13px]">
            <Link
              href="/funding"
              className="font-semibold underline underline-offset-4"
              style={{ color: C.deep }}
            >
              Compare all 22 banks &rarr;
            </Link>
          </p>
        </section>
      </div>

      <Footer />
    </main>
  );
}
