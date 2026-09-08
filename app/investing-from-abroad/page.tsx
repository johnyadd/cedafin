import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import Footer from "@/components/Footer";
import { BRAND } from "@/lib/brand";
import { getAccessRecords } from "@/lib/data/funds";

/**
 * app/investing-from-abroad/page.tsx
 *
 * WHY THIS PAGE IS SHORT, AND WHY THAT IS THE POINT
 * Ghanaians abroad sent home US$7.8 billion in 2025. Both the Bank of Ghana
 * and the SEC are working to move some of it from consumption into investment.
 * And the first question anybody asks — can I open an account without
 * travelling to Ghana — is answered in public by almost nobody.
 *
 * So this page has very few entries. That is not an incomplete page; it is the
 * finding. A directory implying more access than exists would be worse than a
 * short list saying what is actually established.
 *
 * WHY IT READS FROM THE DATABASE
 * The entries come from the access_requirements field, which is populated only
 * where a provider states something in their own material. As replies arrive
 * the page fills itself, and nobody has to remember to update a hand-written
 * list.
 *
 * WHAT IT REFUSES TO DO
 * Infer. An online form is not a policy. A product with a GH¢5 minimum and a
 * mobile money requirement is not thereby available to somebody in London.
 * Where a provider has not said, the page says they have not said.
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
  bg: "#F2F6F9",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
};

export const metadata = {
  title: "Investing in Ghana from abroad — what providers actually say",
  description:
    "Can a Ghanaian living overseas open an investment account without travelling home? What each provider states in their own material, and how much of it is simply unpublished.",
  keywords: [
    "invest in Ghana from abroad",
    "Ghana diaspora investment",
    "non-resident Ghana investment account",
    "Ghanaian abroad mutual fund",
  ],
};

/** Plain labels, since an asset_class value means nothing to a reader. */
const KIND: Record<string, string> = {
  money_market: "Money market fund",
  fixed_income: "Fixed income fund",
  balanced: "Balanced",
  equity: "Shares",
  government_security: "Government Treasury bills",
  commodity: "Gold",
  real_estate: "Property",
};

/*
  Seven questions, and the ceiling is deliberate.

  The original five bundled funding and withdrawal into one, which is the
  wrong way round. Getting money IN is the question people ask; getting it
  OUT is the one that traps them. Separated.

  Minimum, cost and currency were missing entirely, and any of the three can
  rule a provider out before the access questions matter at all.

  More than seven reads as a questionnaire and gets ignored. A provider
  should be able to answer all of these in one reply without consulting
  anybody.
*/
const ASK = [
  "Do you accept applications from someone resident outside Ghana?",
  "Which identity documents — is a passport enough, or is a Ghana Card required? Do you need proof of my address abroad?",
  "Can the whole application be completed remotely, or does some part need me in Ghana?",
  "Do I need a Ghanaian bank account or mobile money wallet before I can start?",
  "How would I fund the account from abroad — international transfer, card, or something else?",
  "How would I get money out, and can it go to a bank account outside Ghana?",
  "What is the minimum to open, what does it cost me a year, and which currency am I holding?",
];

export const revalidate = 3600;

export default async function InvestingFromAbroadPage() {
  const records = await getAccessRecords();

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
          For Ghanaians abroad
        </p>
        <h1
          className="mt-2 text-[1.9rem] font-bold leading-[1.12] sm:text-[2.4rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.02em",
          }}
        >
          Can you invest in Ghana without going there?
        </h1>
        <p
          className="mt-5 text-[16.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          It is the first question, and the one that decides everything — not
          the charge, not the return, but whether the thing is reachable at all.
          Here is what Ghanaian providers state in their own material. There is
          not much of it, and that is the finding rather than a gap in this
          page.
        </p>

        <hr
          className="mt-8 w-14"
          style={{ borderColor: C.gold, borderTopWidth: "3px" }}
        />

        <h2
          className="mt-10 text-[1.4rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What providers actually publish
        </h2>

        {records.length === 0 ? (
          <p className="mt-4 text-[15px]" style={{ color: C.muted }}>
            Nothing yet. We have asked.
          </p>
        ) : (
          <div className="mt-5 space-y-3">
            {records.map((r: (typeof records)[number]) => (
              <section
                key={r.slug}
                className="overflow-hidden rounded-2xl"
                style={{ background: C.card, border: `1px solid ${C.rule}` }}
              >
                <div className="flex">
                  <span
                    className="w-1 shrink-0"
                    style={{ background: C.deep }}
                    aria-hidden="true"
                  />
                  <div className="flex-1 p-5">
                    <p className="text-[15px] font-bold">{r.name}</p>
                    <p
                      className="mt-0.5 text-[11.5px] font-semibold uppercase tracking-[0.1em]"
                      style={{ color: C.gold }}
                    >
                      {r.providerName}
                      {r.assetClass && KIND[r.assetClass] && (
                        <> &middot; {KIND[r.assetClass]}</>
                      )}
                    </p>
                    {/* What it invests in, where the asset class does not say
                        — discretionary management being the obvious case. */}
                    {r.eligibilityNotes && (
                      <p
                        className="mt-2 text-[13px] leading-relaxed"
                        style={{ color: C.muted }}
                      >
                        {r.eligibilityNotes}
                      </p>
                    )}
                    <p
                      className="mt-2.5 text-[14px] leading-relaxed"
                      style={{ color: C.muted }}
                    >
                      {r.accessRequirements}
                    </p>
                    <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[12.5px]">
                      {r.peerGroup && (
                        <Link
                          href={`/compare/${r.peerGroup.replace(":", "-")}`}
                          className="font-semibold underline underline-offset-4"
                          style={{ color: C.deep }}
                        >
                          Compare charges and returns &rarr;
                        </Link>
                      )}
                      {/* Brokers have no provider page — they live on the
                          brokers listing — so the link has to know which
                          kind of firm it points at. */}
                      {r.providerSlug && (
                        <Link
                          href={
                            r.providerSlug.startsWith("broker-")
                              ? "/brokers"
                              : `/providers/${r.providerSlug}`
                          }
                          className="underline underline-offset-4"
                          style={{ color: C.muted }}
                        >
                          {r.providerSlug.startsWith("broker-")
                            ? "All 24 stockbrokers"
                            : `About ${r.providerName}`}
                        </Link>
                      )}
                    </p>
                    {r.accessVerifiedOn && (
                      <p
                        className="mt-2.5 text-[11.5px]"
                        style={{ color: C.muted }}
                      >
                        Read from their own material on{" "}
                        {new Date(
                          r.accessVerifiedOn + "T00:00:00Z",
                        ).toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "long",
                          year: "numeric",
                          timeZone: "UTC",
                        })}
                        .
                      </p>
                    )}
                  </div>
                </div>
              </section>
            ))}
          </div>
        )}

        <section
          className="mt-6 rounded-2xl p-5"
          style={{ background: C.card, border: `1px solid ${C.gold}` }}
        >
          <h3 className="text-[14px] font-bold">
            And everyone else says nothing
          </h3>
          <p
            className="mt-2 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            We track 106 Ghanaian funds and twenty-four licensed
            stockbrokers. The entries above are what we could find published
            about access, from anybody.
            <br />
            <br />
            {/* Was "not one broker states whether they will open an account
                for someone living abroad". One does, and continuing to assert
                an absence after finding the exception is the error this site
                exists to point out. */}
            <strong style={{ color: C.ink }}>
              One broker is an exception.
            </strong>{" "}
            Databank Brokerage state on their own site that they facilitate
            trading for both local and foreign investors, individuals and
            institutions alike — and their account opening form provides for
            non-resident applicants, with a field for a foreign tax
            identification number and proof of a foreign address among the
            documents. What that means for a particular applicant is not
            stated. The other twenty-three publish nothing on the question.
          </p>
          <p
            className="mt-2.5 text-[13.5px] leading-relaxed"
            style={{ color: C.ink }}
          >
            <strong>This page will get longer.</strong> We ask providers what a
            diaspora investor needs, and publish whatever comes back, cited and
            dated.
          </p>
          <p
            className="mt-2 text-[13px] leading-relaxed"
            style={{ color: C.muted }}
          >
            We hold no price history for the products above. Where a provider
            sends one it appears on their page, with the charges beside it.
          </p>
        </section>

        <h2
          className="mt-10 text-[1.4rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What to ask before you send money
        </h2>
        <p className="mt-3 text-[15px] leading-relaxed" style={{ color: C.muted }}>
          Ask before, not after. Five questions, and any provider can answer all
          of them in one reply.
        </p>
        <ol className="mt-4 space-y-2.5">
          {ASK.map((q, i) => (
            <li key={q} className="flex items-baseline gap-3 text-[15px]">
              <span
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[12px] font-bold text-white"
                style={{ background: C.deep }}
              >
                {i + 1}
              </span>
              <span>{q}</span>
            </li>
          ))}
        </ol>
        <p
          className="mt-4 text-[14px] leading-relaxed"
          style={{ color: C.muted }}
        >
          If you get an answer, send it to us and we will publish it on that
          provider&rsquo;s page, cited and dated, so the next person does not
          have to ask.{" "}
          <a
            href={`mailto:${BRAND.dataEmail}?subject=Non-resident%20access`}
            className="font-semibold underline underline-offset-4"
            style={{ color: C.deep }}
          >
            {BRAND.dataEmail}
          </a>
        </p>

        <h2
          className="mt-10 text-[1.4rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Two things worth knowing regardless
        </h2>
        <div className="mt-4 space-y-4 text-[15px] leading-relaxed">
          <p>
            <strong>An online form is not a policy.</strong> Several Ghanaian
            providers have web application forms, and some of those forms have
            fields for a foreign address. That establishes that the form
            accommodates a non-resident. It does not establish that the
            application will be accepted, and we do not present it as though it
            does.
          </p>
          <p>
            <strong>The exchange rate will matter more than the fund.</strong>{" "}
            Whatever you invest in, the rate you get moving money in and out is
            likely to move your outcome more than the difference between one
            product and another.{" "}
            <Link
              href="/insights/three-cedi-exchange-rates"
              className="font-semibold underline underline-offset-4"
              style={{ color: C.deep }}
            >
              How to tell whether your rate is any good
            </Link>
            .
          </p>
        </div>

        <p className="mt-8 text-[13px]">
          <Link
            href="/insights/sending-money-home-is-not-investing-it"
            className="underline underline-offset-4"
            style={{ color: C.deep }}
          >
            Why sending money home is not the same as investing it &rarr;
          </Link>
        </p>
      </div>

      <Footer />
    </main>
  );
}
