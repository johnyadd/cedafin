/**
 * components/Faq.tsx — questions people actually search, answered from the data.
 *
 * WHY THIS EXISTS
 * Google surfaces question-and-answer content directly in results, as
 * expandable panels beneath a listing. That takes more space than an ordinary
 * result and answers the question before anyone clicks — which sounds like a
 * loss until you notice that the site answering is the one named.
 *
 * THE RULE THAT MATTERS
 * The structured data below must match text visible on the page. Marking up
 * answers a visitor cannot see is against Google's guidelines and is
 * penalised, so every question here renders as readable content and the schema
 * is generated from the same array. They cannot drift apart.
 *
 * WHY THESE QUESTIONS
 * Each is answerable from figures this site holds and dates. Nothing here is
 * general advice — "what is a mutual fund" is answered better elsewhere and
 * would rank behind a hundred other pages. "What is the minimum to start
 * investing in Ghana" is answerable only by someone holding the minimums, and
 * that is us.
 *
 * WHY THE ANSWERS CARRY DATES
 * A figure without a date ages silently. These say when they were true, which
 * is both honest and the thing that distinguishes them from the many pages
 * repeating a rate somebody read in 2023.
 */

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  gold: "#E8A33D",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
};

/**
 * Both the visible content and the structured data come from this array, so
 * the markup can never claim something the page does not say.
 */
const QA: { q: string; a: string }[] = [
  {
    q: "What is the minimum to start investing in Ghana?",
    a: "GH₵20 opens the cheapest money market fund we can verify, Stanbic Cash Trust. Most Ghanaian funds ask around GH₵100. One unit of the NewGold ETF is about GH₵462, and the cheapest Ghana Gold Coin is GH₵13,803 — roughly 690 times the fund minimum. A listed share can cost as little as 10 pesewas, but no broker publishes a minimum trade size, so whether a very small purchase is accepted is not something anyone can tell you in advance.",
  },
  {
    q: "What do Ghanaian mutual funds charge?",
    a: "Of the funds that publish enough for us to verify, annual charges run from 1.75% to 2.25%. First Atlantic Income Fund is the cheapest at 1.75%; Stanbic Cash Trust and Stanbic Income Fund Trust are 2.25%. We have catalogued 75 Ghanaian funds and eight publish enough to compare — the rest are listed with the fields blank, because we do not publish figures we cannot source.",
  },
  {
    q: "What does a Ghanaian stockbroker charge to buy shares?",
    a: "Nobody publishes it. We checked the websites of all twenty-four licensed dealing members of the Ghana Stock Exchange in August 2026. Not one publishes a commission rate, one publishes a minimum to open an account, and six had no working website at all. An international platform quotes 0.75% for Ghanaian shares; what a member firm in Accra charges is not published anywhere we could find.",
  },
  {
    q: "What are Treasury bill rates in Ghana?",
    a: "As at August 2026, the 91-day bill paid 5.08%, the 182-day 7.08% and the 364-day 11.59%. These have fallen a long way — the 91-day paid over 20% in early 2025. Any article quoting Ghanaian Treasury bill returns should be checked against the date it was written.",
  },
  {
    q: "What do business loans cost in Ghana?",
    a: "For a one-year SME loan reported to Bank of Ghana in May 2026, the cheapest of 22 banks was Standard Chartered at 11.03% APR and the dearest Guaranty Trust at 33.58% — 22.5 percentage points apart. The APR includes fees; the interest rate a bank advertises does not. One bank advertises a minimum of 13.70% and reports a maximum of 23.42%.",
  },
  {
    q: "Can I invest in Ghana from abroad?",
    a: "In principle yes, and in practice nobody publishes what it takes. No Ghanaian fund manager or stockbroker we track states what a non-resident needs to open an account, which documents are required, or how long it takes. We have asked all of them and will publish what comes back. The other thing to know is that the exchange rate usually moves a diaspora investor's outcome more than the fund does.",
  },
];

export default function Faq() {
  return (
    <section className="mt-10">
      {/*
        The schema. Generated from the same array as the visible text below,
        so it cannot describe answers the page does not show — which is both
        Google's requirement and the honest arrangement.
      */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            mainEntity: QA.map(({ q, a }) => ({
              "@type": "Question",
              name: q,
              acceptedAnswer: { "@type": "Answer", text: a },
            })),
          }),
        }}
      />

      <h2
        className="text-[11px] font-semibold uppercase tracking-[0.14em]"
        style={{ color: C.gold }}
      >
        Questions people ask
      </h2>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {QA.map(({ q, a }) => (
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
                  ▸
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

      <p className="mt-3 text-[11.5px]" style={{ color: C.muted }}>
        Figures as at August 2026 unless stated. Every one is taken from a
        document its issuer published, and dated on the page it appears on.
      </p>
    </section>
  );
}
