import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import DataProvenance from "@/components/DataProvenance";
import Footer from "@/components/Footer";
import ShareThis from "@/components/ShareThis";
import { BRAND } from "@/lib/brand";
import { getTbillRates } from "@/lib/data/funds";

/**
 * app/savings/page.tsx — what a Ghanaian bank pays you, and what it wants
 * first.
 *
 * WHY THIS PAGE EXISTS
 * The site had a page for every way of placing money except the one most
 * Ghanaians actually use. Funds, Treasury bills, shares, gold — and nothing
 * at all on a bank account.
 *
 * THE FINDING, WHICH THE STRUCTURE FOLLOWS
 * Every published deposit rate we found carries a condition that changes it.
 * Not a footnote — the condition is usually the whole story. An account
 * advertising up to 8% pays nothing at all until the balance reaches
 * GHS 15,000. One paying 7% pays 3% if you touch it inside a year. One is
 * quoted as two points above a number the bank does not publish.
 *
 * So the table shows the rate and the condition in the same row, because
 * showing the rate alone would repeat the thing the page objects to.
 *
 * WHY THE FIGURES ARE HARD-CODED
 * There is no deposit product table in the database — these were read from
 * bank pages by hand. The page says so rather than implying a pipeline that
 * does not exist. When enough banks publish to make a series worth holding,
 * that changes.
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
  title: "What Ghanaian banks pay on savings — and what they want first",
  description:
    "Three of twenty-one Ghanaian banks publish a savings rate. Every one attaches a condition that changes it: a minimum balance to earn anything, a withdrawal that forfeits the interest, or a rate quoted above an unpublished number.",
  keywords: [
    "savings account interest rate Ghana",
    "Ghana bank savings rates",
    "best savings account Ghana",
    "fixed deposit rate Ghana",
  ],
};

type Account = {
  bank: string;
  name: string;
  headline: string;
  /** The thing that changes the headline. This is the story. */
  condition: string;
  minimum: string;
};

const ACCOUNTS: Account[] = [
  {
    bank: "Republic Bank (Ghana)",
    name: "Optimizer",
    headline: "up to 8%",
    condition:
      "Nothing is earned until the balance reaches GHS 15,000. Two withdrawals a month for individuals; a third costs GHS 10. Interest applied quarterly on the average monthly balance.",
    minimum: "GHS 1,000 to operate",
  },
  {
    bank: "Republic Bank (Ghana)",
    name: "55plus",
    headline: "up to 8%",
    condition:
      "Ghanaians over 55 only. A minimum monthly balance of GHS 1,000 must be held to earn anything. Applied quarterly.",
    minimum: "GHS 50 to open, no operating minimum",
  },
  {
    bank: "Republic Bank (Ghana)",
    name: "iDO",
    headline: "5% a year",
    condition:
      "No withdrawal for six months after opening. A withdrawal inside six months forfeits that quarter's interest.",
    minimum: "GHS 200",
  },
  {
    bank: "Fidelity Bank Ghana",
    name: "SMART Goal",
    headline: "up to 7%",
    condition:
      "Falls to 3% if the money is withdrawn before the twelve-month tenor.",
    minimum: "GH¢30",
  },
  {
    bank: "Fidelity Bank Ghana",
    name: "Smart Account",
    headline: "up to 3%",
    condition:
      "Interest is forfeited if more than two withdrawals are made in a month.",
    minimum: "—",
  },
  {
    bank: "Fidelity Bank Ghana",
    name: "Savings (Reserve)",
    headline: "up to 2.5%",
    condition: "Tiered. A minimum balance of GH¢500 is needed to earn anything.",
    minimum: "GH¢500 to earn interest",
  },
  {
    bank: "Guaranty Trust Bank (Ghana)",
    name: "Target Savings",
    headline: "2% above their savings rate",
    condition:
      "The savings rate it is measured against is not published, so the figure cannot be worked out. Bonus interest is forfeited if the average balance falls below GH¢200.",
    minimum: "No initial deposit required",
  },
];

const ASK = [
  "What balance do I need before I earn anything? This is the question, not the rate. Two of the accounts above pay nothing at all below a threshold.",
  "Is it per annum, and when is it applied? A rate credited quarterly on the minimum monthly balance is not the same as one paid on what you actually held.",
  "What happens if I withdraw? Three of these accounts reduce or forfeit interest on a withdrawal, and one does so for six months after opening.",
  "Is there a monthly fee? A GHS 20 monthly charge on a GHS 1,000 balance costs more than 2% a year pays.",
  "And what does the government pay? Treasury bills are the benchmark, they are available from GHS 5, and a bank account paying less than the bill is worth knowing about before you open it rather than after.",
];

export const revalidate = 3600;

export default async function SavingsPage() {
  const rates = await getTbillRates();
  const tbill = rates.find((r) => r.days === 91) ?? rates[0] ?? null;

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
          Money in a bank account
        </p>
        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.1] sm:text-[2.4rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.02em",
          }}
        >
          Every published savings rate in Ghana has a condition attached
        </h1>
        <p
          className="mt-5 text-[16.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          Three of twenty-one banks publish what they pay a saver. Each one
          attaches something that changes the number — a balance you must hold
          before you earn anything, a withdrawal that forfeits the interest, or
          a rate quoted above a figure they do not publish.
        </p>

        {/* Rate and condition in the same row. Showing the rate alone would
            repeat the thing this page objects to. */}
        <h2
          className="mt-10 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What they pay, and what they want first
        </h2>
        <div className="mt-4 space-y-2">
          {ACCOUNTS.map((a) => (
            <div
              key={`${a.bank}-${a.name}`}
              className="rounded-2xl p-4 sm:p-5"
              style={{ background: C.card, border: `1px solid ${C.rule}` }}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <div>
                  <p className="text-[14.5px] font-bold">{a.name}</p>
                  <p className="text-[12px]" style={{ color: C.muted }}>
                    {a.bank}
                  </p>
                </div>
                <span
                  className="text-[1.25rem] font-bold tabular-nums"
                  style={{ color: C.deep }}
                >
                  {a.headline}
                </span>
              </div>
              <p
                className="mt-2.5 text-[13.5px] leading-relaxed"
                style={{ color: C.clay }}
              >
                {a.condition}
              </p>
              <p className="mt-1.5 text-[12px]" style={{ color: C.muted }}>
                Minimum: {a.minimum}
              </p>
            </div>
          ))}
        </div>

        {/* The benchmark, live. */}
        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What the government pays
        </h2>
        <div
          className="mt-4 overflow-hidden rounded-2xl"
          style={{ background: C.card, border: `1px solid ${C.good}` }}
        >
          <div className="flex">
            <span className="w-1 shrink-0" style={{ background: C.good }} aria-hidden="true" />
            <div className="flex-1 p-5">
              {tbill && (
                <p className="text-[15px]">
                  The {tbill.days}-day Treasury bill last cleared at{" "}
                  <strong style={{ color: C.good }}>
                    {tbill.ratePct.toFixed(2)}% a year
                  </strong>
                  {tbill.asOf ? ` (${tbill.asOf})` : ""}.
                </p>
              )}
              <p
                className="mt-2.5 text-[14px] leading-relaxed"
                style={{ color: C.muted }}
              >
                No minimum balance to earn it, no withdrawal condition, and no
                monthly fee. Ecobank&rsquo;s TBill4All sells them from GHS 5
                through mobile money without a bank account; IC&rsquo;s
                Liquidity Fund holds much the same instruments from GH₵1.
              </p>
              <p className="mt-2.5 text-[13.5px]">
                <Link
                  href="/treasury-bill-calculator"
                  className="font-semibold underline underline-offset-4"
                  style={{ color: C.deep }}
                >
                  What a Treasury bill would pay you &rarr;
                </Link>
              </p>
            </div>
          </div>
        </div>

        <div
          className="mt-6 rounded-2xl p-5"
          style={{ background: "#FFF8EC", border: `1px solid ${C.gold}` }}
        >
          <p className="text-[14.5px] font-bold">
            The headline rates are for people who already have money
          </p>
          <p
            className="mt-2 text-[14px] leading-relaxed"
            style={{ color: C.muted }}
          >
            A saver with GHS 500 earns nothing on Republic&rsquo;s Optimizer,
            which needs GHS 15,000 before it pays at all, and nothing on
            Fidelity&rsquo;s Reserve account, which needs GH¢500. The same
            GHS 500 in a Treasury bill earns the rate above from the first day.
          </p>
          <p
            className="mt-2.5 text-[14px] leading-relaxed"
            style={{ color: C.muted }}
          >
            That is not a criticism of the banks — a small balance costs them
            more to administer than it earns. It is a reason for a saver to
            know what else exists.
          </p>
        </div>

        {/* The absence. */}
        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Eighteen banks publish nothing
        </h2>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          We read the savings and account pages of every Ghanaian bank whose
          site we could reach. Three publish a rate. The rest describe their
          accounts — the card, the app, the branch network — and not what the
          money earns.
        </p>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          Several publish a minimum balance without publishing what that
          balance would earn, which is the least useful half of the pair.
        </p>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Five things to ask before you open one
        </h2>
        {/* A ul, not an ol — the numbers are drawn below, and an ol would
            add its own on top of them. */}
        <ul className="mt-4 space-y-3 list-none">
          {ASK.map((q, i) => (
            <li key={i} className="flex gap-3">
              <span
                className="mt-0.5 shrink-0 text-[13px] font-bold tabular-nums"
                style={{ color: C.gold }}
              >
                {i + 1}
              </span>
              <span className="text-[14.5px] leading-relaxed">{q}</span>
            </li>
          ))}
        </ul>

        <ShareThis
          path="/savings"
          audience="somebody with money sitting in a Ghanaian bank account"
          message="Every published Ghanaian savings rate has a condition attached. One account pays nothing until the balance reaches GHS 15,000."
        />

        <DataProvenance
          title="Ghanaian bank savings rates and conditions"
          source="each bank's own website and published tariff guides"
          covering="21 of 23 licensed banks read; 3 publish a rate"
          checked="September 2026"
          method="Read from the banks' own pages by hand. There is no deposit product series in our database yet — these figures are not extracted on a schedule, and the page says so rather than implying a pipeline that does not exist."
          pageUrl="https://cedafin.com/savings"
        />

        <p className="mt-6 text-[12.5px] leading-relaxed" style={{ color: C.muted }}>
          {BRAND.legalStatus} If you are a bank and we have your terms wrong,
          or you publish a rate we have missed, tell us and we will correct it
          the same day.
        </p>
      </div>

      <Footer />
    </main>
  );
}
