/**
 * app/funding/page.tsx — what borrowing costs a Ghanaian business.
 *
 * WHY /funding AND NOT /borrow
 * "Borrow" is right in the database — it is the opposite of "invest" and names
 * the direction money moves. But a founder does not think "I need to borrow",
 * they think "I need funding", and funding covers equity and grants too. The
 * URL is the expensive thing to change later, so it takes the broader word;
 * the heading stays specific to what is actually here.
 *
 * THE FINDING THIS PAGE EXISTS FOR
 * A Ghanaian SME can pay 11.03% or 33.58% for the same one-year facility, in
 * the same month, from two licensed banks. Three times the cost. Bank of Ghana
 * publishes this monthly and it reaches almost nobody.
 *
 * TWO THINGS THE PAGE MUST NOT DO
 *
 *   TREAT A RATE AS A QUOTE. BoG says plainly that a typical customer may be
 *   offered something different after assessment. Every figure here is
 *   indicative and the page says so beside the numbers, not in a footer. A
 *   business that reads 11.03% as an offer and budgets on it has been misled
 *   by us, not by the bank.
 *
 *   HIDE THE FEES. The advertised lending rate and the APR are both shown
 *   because the gap between them is the point: Agricultural Development Bank
 *   lends at 19.59% and costs 28.13%, while Access Bank's gap is 0.03. Rank on
 *   the headline rate and those two look comparable. They are not.
 */

import Link from "next/link";

import Footer from "@/components/Footer";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";
import { notFound } from "next/navigation";

import { BRAND } from "@/lib/brand";
import { creditLabel, getLending, type LendingRow } from "@/lib/data/funds";

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
  bg: "#F2F6F9",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
  good: "#0E8F62",
};

const CATEGORIES = [
  { key: "sme_credit", label: "Business loans" },
  { key: "personal_credit", label: "Personal loans" },
  { key: "corporate_credit", label: "Corporate loans" },
];

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export const metadata = {
  title: "SME and business loan rates in Ghana — 22 banks compared",
  description:
    "What Ghanaian banks actually charge for business, personal and corporate credit, from Bank of Ghana's own APR returns. The rate with the fees counted.",
};
export const revalidate = 3600;

export default async function FundingPage({
  searchParams,
}: {
  searchParams: Promise<{ type?: string; term?: string }>;
}) {
  const sp = await searchParams;
  const category = CATEGORIES.find((c) => c.key === sp.type)?.key ?? "sme_credit";
  const tenor = [1, 3, 5].includes(Number(sp.term)) ? Number(sp.term) : 1;

  const all = await getLending(category);
  if (all.length === 0) notFound();

  const rows = all
    .filter((r) => r.tenorYears === tenor)
    .sort((a, b) => (a.aprPct ?? 999) - (b.aprPct ?? 999));

  const aprs = rows.map((r) => r.aprPct).filter((v): v is number => v !== null);
  const cheapest = aprs.length ? Math.min(...aprs) : null;
  const dearest = aprs.length ? Math.max(...aprs) : null;
  const asOf = rows.find((r) => r.asOf)?.asOf ?? null;
  const label = CATEGORIES.find((c) => c.key === category)!.label;

  // How much more the dearest lender costs on a GH¢100,000 facility, per year.
  const extraOn100k =
    cheapest !== null && dearest !== null
      ? Math.round(((dearest - cheapest) / 100) * 100_000)
      : null;

  return (
    <main
      className={`${display.variable} ${body.variable} min-h-screen`}
      style={{ background: C.bg, color: C.ink, fontFamily: "var(--font-body)" }}
    >
      <div
        className="w-full px-5 py-2 text-center text-[11px] font-medium tracking-wide text-white"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        Bank of Ghana published rates
        {asOf ? ` · ${fmtDate(asOf)}` : ""} · indicative, not quotes
      </div>

      <div className="mx-auto max-w-4xl px-5 py-8 sm:px-8 sm:py-10">
        <section
          className="overflow-hidden rounded-3xl p-7 text-white sm:p-10"
          style={{
            background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 62%, ${C.gold} 190%)`,
          }}
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] opacity-80">
            {label} · {tenor} year{tenor > 1 ? "s" : ""}
          </p>
          <h1
            className="mt-3 text-[2.1rem] font-bold leading-[1.08] sm:text-[3rem]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            The same loan,
            <br />
            three times the price.
          </h1>

          {cheapest !== null && (
            <div className="mt-8 grid grid-cols-3 gap-4 sm:max-w-lg">
              {[
                { k: "Cheapest bank", v: `${cheapest.toFixed(2)}%`, hi: true },
                { k: "Dearest bank", v: `${dearest!.toFixed(2)}%` },
                { k: "Banks compared", v: String(rows.length) },
              ].map(({ k, v, hi }) => (
                <div key={k}>
                  <p className="text-[10px] uppercase tracking-wider opacity-75">
                    {k}
                  </p>
                  <p
                    className="mt-1 text-[1.6rem] font-bold tabular-nums leading-none sm:text-[2rem]"
                    style={{ color: hi ? C.gold : "#fff" }}
                  >
                    {v}
                  </p>
                </div>
              ))}
            </div>
          )}

          {extraOn100k !== null && extraOn100k > 0 && (
            <p className="mt-7 max-w-xl text-[14px] leading-relaxed opacity-90">
              On a GH&#8373;100,000 facility that difference is about{" "}
              <strong>GH&#8373;{extraOn100k.toLocaleString()}</strong> a year —
              for the same money, over the same term, from banks the same
              regulator licenses.
            </p>
          )}
        </section>

        {/* Filters. Stated criteria, not a recommendation. */}
        <nav className="mt-7 flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <Link
              key={c.key}
              href={`/funding?type=${c.key}&term=${tenor}`}
              className="rounded-full px-4 py-2 text-[13px] font-semibold"
              style={{
                background: c.key === category ? C.deep : C.card,
                color: c.key === category ? "#fff" : C.ink,
                border: `1px solid ${c.key === category ? C.deep : C.rule}`,
              }}
            >
              {c.label}
            </Link>
          ))}
        </nav>
        <nav className="mt-2 flex flex-wrap gap-2">
          {[1, 3, 5].map((t) => (
            <Link
              key={t}
              href={`/funding?type=${category}&term=${t}`}
              className="rounded-full px-4 py-1.5 text-[12.5px] font-semibold"
              style={{
                background: t === tenor ? `${C.teal}1A` : C.card,
                color: t === tenor ? C.deep : C.muted,
                border: `1px solid ${t === tenor ? C.teal : C.rule}`,
              }}
            >
              {t} year{t > 1 ? "s" : ""}
            </Link>
          ))}
        </nav>

        {/*
          Placed above the rate list, because someone who has not yet worked out
          what they need should not have to read 22 bank rows first. Someone who
          knows exactly what they want will scroll past it.
        */}
        <Link
          href="/funding/match"
          className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl px-5 py-4"
          style={{ background: `${C.gold}14`, border: `1px solid ${C.gold}` }}
        >
          <span className="text-[13.5px]">
            <strong>Not sure which of these you&rsquo;d qualify for?</strong>{" "}
            Answer nine questions and we&rsquo;ll show what each would cost you.
          </span>
          <span
            className="shrink-0 rounded-full px-4 py-2 text-[12.5px] font-bold text-white"
            style={{ background: "#7A3E12" }}
          >
            Work it out →
          </span>
        </Link>

        {/*
          Not a tab, deliberately. The tabs filter bank products by type and
          term; equity has no APR, no term and no comparable rows, so putting
          it among them would break the comparison rather than extend it.

          A link down to it does the job — a business owner who reads "loan"
          and thinks "that is not what I need" now has somewhere to go.
        */}
        <p className="mt-3 text-[13px]">
          <a
            href="#private-capital"
            className="font-semibold underline underline-offset-4"
            style={{ color: "#7A3E12" }}
          >
            Not a loan? Nine licensed funds provide equity and private debt
            &darr;
          </a>
        </p>

        <p
          className="mt-5 rounded-2xl px-5 py-4 text-[13px] leading-relaxed"
          style={{ background: `${C.gold}1A` }}
        >
          <strong>These are indicative rates, not offers.</strong> Bank of Ghana
          publishes them so borrowers can compare. What any bank actually offers
          you depends on its assessment of your business — your trading history,
          security, and accounts. Treat this as where to start asking, not what
          you will pay.
        </p>

        <ol className="mt-6 space-y-3">
          {rows.map((r, i) => {
            const isCheapest = r.aprPct !== null && r.aprPct === cheapest;
            const width =
              r.aprPct !== null && cheapest !== null && dearest !== null &&
              dearest !== cheapest
                ? 14 + ((r.aprPct - cheapest) / (dearest - cheapest)) * 86
                : 100;
            return (
              <li
                key={r.id}
                className="rounded-2xl p-5"
                style={{
                  background: C.card,
                  border: `1px solid ${isCheapest ? C.gold : C.rule}`,
                }}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span
                      className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold"
                      style={{
                        background: isCheapest ? C.gold : `${C.teal}1A`,
                        color: isCheapest ? C.ink : C.deep,
                      }}
                    >
                      {i + 1}
                    </span>
                    <div className="min-w-0">
                      <h2 className="text-[15.5px] font-bold leading-snug">
                        {r.provider.name}
                      </h2>
                      <p className="mt-0.5 text-[12px]" style={{ color: C.muted }}>
                        {creditLabel(r.category)} · {r.tenorYears} year
                        {r.tenorYears > 1 ? "s" : ""}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-[1.5rem] font-bold tabular-nums leading-none">
                      {r.aprPct !== null ? `${r.aprPct.toFixed(2)}%` : "—"}
                    </p>
                    <p className="mt-0.5 text-[10.5px]" style={{ color: C.muted }}>
                      all-in cost a year
                    </p>
                  </div>
                </div>

                <div
                  className="mt-4 h-1.5 w-full overflow-hidden rounded-full"
                  style={{ background: C.rule }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${width}%`,
                      background: isCheapest
                        ? `linear-gradient(90deg, ${C.deep}, ${C.gold})`
                        : C.teal,
                    }}
                  />
                </div>

                {/* The gap is the point: fees a headline rate does not show. */}
                {r.lendingRatePct !== null && (
                  <p className="mt-3 text-[12.5px]" style={{ color: C.muted }}>
                    Advertised rate{" "}
                    <strong style={{ color: C.ink }}>
                      {r.lendingRatePct.toFixed(2)}%
                    </strong>
                    {r.feeGapPct !== null && r.feeGapPct > 0.05 ? (
                      <>
                        {" "}
                        — fees add{" "}
                        <strong style={{ color: C.clay }}>
                          {r.feeGapPct.toFixed(2)} points
                        </strong>
                        .
                      </>
                    ) : (
                      <> — no additional charges reported.</>
                    )}
                  </p>
                )}
              </li>
            );
          })}
        </ol>

{/*
  Equity and private debt — the option the borrowing pages never mention.

  WHY IT BELONGS HERE
  Everything else on the borrow side of this site is bank credit: 157 products
  across 22 banks, compared on APR. A business owner reading it would conclude
  that borrowing from a bank is the only route, because nothing here says
  otherwise.

  Ghana has nine SEC-licensed private funds providing equity and private debt.
  All nine have working websites — better than the twenty-four stockbrokers,
  six of whose registered sites did not respond. Four publish a visible way for
  a founder to make contact. Two publish what size of investment they make.

  WHY THE TICKET SIZES MATTER MORE THAN ANYTHING ELSE HERE
  Because they answer the only question that decides whether to read on. The
  smallest published equity ticket is around GH₵566,000 — more than five times
  the GH₵100,000 the loan comparison on this page assumes. For most businesses
  reading this, that settles it, and saying so saves them the afternoon.

  WHY IT IS NOT A COMPARISON TABLE
  Two of nine publishing a figure is not a market you can compare. A table with
  seven blank rows would imply the blanks are failures rather than the normal
  reticence of an asset class where terms are negotiated per deal.
*/}
<section
  id="private-capital"
  className="mt-10 overflow-hidden rounded-2xl"
  style={{ background: C.card, border: `1px solid ${C.rule}` }}
>
  <div
    className="px-5 py-3.5 text-white sm:px-6"
    style={{ background: `linear-gradient(90deg, #6B3A16, #A9662E)` }}
  >
    <h2
      className="text-[15px] font-bold"
      style={{ fontFamily: "var(--font-display)" }}
    >
      If a loan is the wrong instrument
    </h2>
  </div>

  <div className="p-5 sm:p-6">
    <p className="text-[15px] leading-relaxed">
      Everything above is bank credit — you borrow, you repay, you keep the
      business. Ghana also has nine private funds licensed by the Securities
      and Exchange Commission that provide{" "}
      <strong>equity and private debt</strong>: they take a stake, or lend on
      terms negotiated per deal, and they expect to exit in five to ten years.
    </p>

    <p
      className="mt-3 text-[15px] leading-relaxed"
      style={{ color: C.muted }}
    >
      It suits a different situation. A bank wants security and repayment from
      cash flow. An equity investor wants growth and does not want the money
      back next year — which is the right shape for a business that will lose
      money while it scales, and the wrong shape for one that simply needs
      working capital.
    </p>

    {/* The figure that decides whether to read on. */}
    <div
      className="mt-5 rounded-2xl p-4"
      style={{ background: "#FFF8EC", border: `1px solid ${C.gold}` }}
    >
      <p className="text-[13px] font-bold">
        The first thing to check is the size
      </p>
      <p
        className="mt-2 text-[13.5px] leading-relaxed"
        style={{ color: C.muted }}
      >
        Two of the nine publish what they invest.{" "}
        <strong style={{ color: C.ink }}>Wangara Green Ventures</strong> state
        US$50,000 to US$500,000.{" "}
        <strong style={{ color: C.ink }}>Growth Investment Partners</strong>{" "}
        state the cedi equivalent of US$500,000 to US$5 million, with follow-on
        of up to US$5 million more.
      </p>
      <p
        className="mt-2.5 text-[13.5px] leading-relaxed"
        style={{ color: C.muted }}
      >
        At current rates the smallest published ticket is around{" "}
        <strong style={{ color: C.ink }}>GH&#8373;570,000</strong> — over five
        times the GH&#8373;100,000 the loan comparison above assumes. If you
        need less than that, this route is probably not open to you, and the
        banks above are where to look.
      </p>
    </div>

    <h3 className="mt-7 text-[14px] font-bold">
      The nine, by what kind of capital they provide
    </h3>
    <p
      className="mt-2 text-[13.5px] leading-relaxed"
      style={{ color: C.muted }}
    >
      From the Securities and Exchange Commission&rsquo;s register of licensed
      private funds, with what we could find on each of their own sites in
      September 2026. Websites are the ones the register gives.
    </p>

    {/*
      Grouped rather than listed flat.

      "Nine private funds" treats them as interchangeable and they are not. A
      profitable business needing expansion capital wants a different firm from
      a startup, and a business that does not want to give up ownership wants
      the debt fund rather than any of the others. Burying that distinction in
      a list makes the reader do work we could have done for them.

      The groupings come from the fund names and what each site states — a
      fund called "SME Fund" backs established small businesses, one called
      "Private Debt Fund" lends. Where a site says more, that is used instead.
    */}
    <div className="mt-4 space-y-5">
      {(
        [
          [
            "Debt — you keep the business",
            "Lends rather than taking a stake. The closest of these to a bank loan, and the only route here that does not cost you ownership.",
            [
              [
                "Origen Private Debt Fund",
                "ashfieldinvest.com",
                null,
                "Nothing found on ticket size or how to apply. The register gives a website whose domain does not match the fund name, so this may not be theirs.",
              ],
            ],
          ],
          [
            "Growth and expansion capital",
            "For businesses already trading and profitable, raising to expand. Larger cheques, and they will expect a board seat.",
            [
              [
                "Growth Investment Partners Ghana",
                "gipghana.com",
                "US$500,000 – US$5m, plus follow-on up to US$5m more",
                "Sector stated. Visible route to make contact.",
              ],
              [
                "Mirepa Capital SME Fund 1",
                "mirepaglobal.com",
                null,
                "Backs small and medium businesses, by its own name. Nothing found on ticket size, stage or how to apply.",
              ],
            ],
          ],
          [
            "Venture capital — early stage",
            "For businesses that will lose money while they grow. They expect most of their investments to fail and a few to pay for the rest, which shapes what they look for.",
            [
              [
                "Injaro Ghana Venture Capital Fund",
                "injaroinvestments.com",
                null,
                "Stage and sector stated. Visible route to make contact.",
              ],
              [
                "ISF Ghana Venture Capital",
                "impcapadv.com",
                null,
                "Stage and sector stated. Visible route to make contact.",
              ],
              [
                "Ci GABA VC",
                "siaghana.com",
                null,
                "Sector stated. Visible route to make contact.",
              ],
              [
                "Oasis Africa VC Fund",
                "oasiscapitalghana.com",
                null,
                "Nothing found on ticket size, stage or how to apply.",
              ],
              [
                "Oasis Africa VC Fund II",
                "oasiscapitalghana.com",
                null,
                "Same manager and site as the fund above.",
              ],
            ],
          ],
          [
            "Climate and green ventures",
            "Venture capital with a stated environmental focus. If your business does not fit that, this is not your fund whatever its cheque size.",
            [
              [
                "Wangara Green Ventures",
                "wangaracapital.com",
                "US$50,000 – US$500,000",
                "Stage and sector stated.",
              ],
            ],
          ],
        ] as [string, string, [string, string, string | null, string][]][]
      ).map(([groupName, groupNote, funds]) => (
        <div key={groupName}>
          <p
            className="text-[11px] font-semibold uppercase tracking-[0.12em]"
            style={{ color: "#A9662E" }}
          >
            {groupName}
          </p>
          <p
            className="mt-1 text-[12.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            {groupNote}
          </p>

          <div className="mt-2.5 space-y-2">
            {funds.map(([name, domain, ticket, note]) => (
              <div
                key={name}
                className="flex overflow-hidden rounded-xl"
                style={{ background: C.bg, border: `1px solid ${C.rule}` }}
              >
                <span
                  className="w-1 shrink-0"
                  style={{ background: ticket ? "#A9662E" : C.rule }}
                  aria-hidden="true"
                />
                <div className="flex-1 p-3.5">
                  <p className="flex flex-wrap items-baseline gap-x-2 text-[13.5px]">
                    <strong>{name}</strong>
                    <a
                      href={`https://${domain}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[12px] underline underline-offset-4"
                      style={{ color: C.deep }}
                    >
                      {domain}
                    </a>
                  </p>
                  {ticket && (
                    <p className="mt-1 text-[12.5px] font-semibold">
                      Invests {ticket}
                    </p>
                  )}
                  <p className="mt-1 text-[12px]" style={{ color: C.muted }}>
                    {note}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>

    <p
      className="mt-4 text-[12.5px] leading-relaxed"
      style={{ color: C.muted }}
    >
      The groupings are ours, drawn from each fund&rsquo;s own name and what
      its site states. Several do not describe themselves in these terms, and a
      fund that says nothing about its stage may well invest across more than
      one of these. Ask before assuming.
    </p>

    <h3 className="mt-6 text-[14px] font-bold">
      What the other seven publish
    </h3>
    <p
      className="mt-2 text-[14px] leading-relaxed"
      style={{ color: C.muted }}
    >
      Not much, and that is normal for the asset class rather than a failing —
      private investment terms are negotiated per deal, so there is no rate card
      to publish. Four of the nine do have a visible route for a founder who
      knows nobody to make contact, which is the thing actually worth knowing.
    </p>
    <p
      className="mt-2 text-[14px] leading-relaxed"
      style={{ color: C.muted }}
    >
      All nine have working websites — which, set against the twenty-four
      licensed stockbrokers where six of the registered sites did not respond,
      is worth noting.
    </p>

    <h3 className="mt-6 text-[14px] font-bold">Before you approach one</h3>
    <ul
      className="mt-2 space-y-2 text-[14px] leading-relaxed"
      style={{ color: C.muted }}
    >
      <li>
        <strong style={{ color: C.ink }}>
          Check they are licensed.
        </strong>{" "}
        The SEC maintains the register of licensed private funds, and has been
        warning the public about unlicensed investment schemes. A fund that is
        not on the register is not one to take money from or give equity to.
      </li>
      <li>
        <strong style={{ color: C.ink }}>
          Understand what you are giving up.
        </strong>{" "}
        Equity is not cheaper money — it is a share of everything the business
        earns afterwards, permanently, plus a say in how it is run. On a
        business that succeeds, it is usually the most expensive capital there
        is.
      </li>
      <li>
        <strong style={{ color: C.ink }}>Ask about the exit.</strong> These
        funds have a fixed life and must return money to their own investors.
        What that means for you in year five is a question to ask in year one.
      </li>
    </ul>

    <p className="mt-5 text-[12.5px]" style={{ color: C.muted }}>
      Nine funds, from the Securities and Exchange Commission&rsquo;s register
      of licensed private funds. Ticket sizes as published by the two funds
      that state them, read from their own sites in September 2026. We are in
      contact with providers to close the gaps, and publish whatever they send,
      cited and dated.
    </p>
  </div>
</section>

        <section
          className="mt-12 rounded-3xl p-6 sm:p-8"
          style={{ background: C.card, border: `1px solid ${C.rule}` }}
        >
          <h2
            className="text-[18px] font-bold"
            style={{ fontFamily: "var(--font-display)" }}
          >
            What this page doesn&rsquo;t show
          </h2>
          <ul
            className="mt-4 space-y-3 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            <li>
              <strong style={{ color: C.ink }}>Whether you&rsquo;ll qualify.</strong>{" "}
              The binding question for most Ghanaian businesses isn&rsquo;t the
              rate, it&rsquo;s access. Bank capital rules make small loans
              costly to process, so many applications are refused regardless of
              the business.
            </li>
            <li>
              <strong style={{ color: C.ink }}>Anyone but banks.</strong>{" "}
              Microfinance institutions, savings and loans companies and digital
              lenders aren&rsquo;t in Bank of Ghana&rsquo;s APR report — and
              they&rsquo;re where businesses refused by banks actually borrow.
            </li>
            <li>
              <strong style={{ color: C.ink }}>Security and covenants.</strong>{" "}
              What a bank asks you to pledge can matter more than the rate.
            </li>
          </ul>
          <p className="mt-6 text-[11px] leading-relaxed" style={{ color: C.muted }}>
            {BRAND.legalStatus} We are not a credit broker and do not arrange
            finance.
          </p>
        </section>

        <p className="mt-8 text-[13px]">
          <Link
            href="/"
            className="underline underline-offset-4"
            style={{ color: C.deep }}
          >
            ← Investing side
          </Link>
        </p>
      </div>
      <Footer />
    </main>
  );
}
