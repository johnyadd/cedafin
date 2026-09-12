import Link from "next/link";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

import DataProvenance from "@/components/DataProvenance";
import Footer from "@/components/Footer";
import { BRAND } from "@/lib/brand";
import { getDisclosure } from "@/lib/data/funds";

/**
 * app/what-gets-published/page.tsx
 *
 * WHY THIS PAGE EXISTS
 * Every other page here reports what providers publish. This one reports what
 * they do not — and that is a harder thing to know, because absence cannot be
 * scraped.
 *
 * A crawler records what it finds. Establishing that twenty-four of
 * twenty-four Ghanaian brokers publish no commission rate requires visiting
 * all twenty-four, finding nothing, and writing down that nothing was found,
 * with the date. The record of having looked is the asset.
 *
 * WHY IT NAMES WHO PUBLISHES AND NOT WHO DOES NOT
 * The same data can be a table of six firms who disclose or a table of
 * ninety-one who do not. The first is generous and creates a reason to
 * publish; the second is an accusation, and an unfair one — a firm nobody has
 * asked is not withholding anything.
 *
 * So the counts carry the finding and the names carry the credit. Anyone who
 * wants the full picture can read the provider pages, where every blank field
 * is visible with the date we last looked.
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
  title: "What Ghanaian providers publish — and what they don't",
  description:
    "A dated record of what Ghana's licensed funds, brokers and lenders disclose about charges, minimums and access. Most of it is not published, and that is the finding.",
};

/** What each field means to somebody deciding, and why its absence costs. */
const FIELDS: Record<
  string,
  { label: string; whoFor: string; matters: string }
> = {
  charges: {
    label: "What the fund charges a year",
    whoFor: "collective investment schemes",
    matters:
      "Two funds holding the same instruments can differ by more than two percentage points a year. Over a decade that is most of the difference between them, and it is the one thing a saver can actually control.",
  },
  minimum: {
    label: "The minimum to open",
    whoFor: "collective investment schemes",
    matters:
      "Somebody with GH₵500 cannot tell which funds would take them. The published minimums we have found run from GH₵1 to the cedi equivalent of US$20,000.",
  },
  commission: {
    label: "What a trade costs",
    whoFor: "licensed stockbrokers",
    matters:
      "There is no published commission rate anywhere in Ghana. A buyer of shares cannot establish the cost of buying them until they have opened an account with somebody.",
  },
  non_resident_access: {
    label: "Whether somebody abroad can open an account",
    whoFor: "every provider",
    matters:
      "Ghanaians abroad sent home US$7.8bn in 2025. Almost none of them can establish, before committing money, whether a given Ghanaian product is open to them at all.",
  },
  custody: {
    label: "Whether securities can be held on your behalf",
    whoFor: "licensed stockbrokers",
    matters:
      "Relevant to anyone who cannot easily maintain a securities account in their own name, which includes many people living outside Ghana.",
  },
  lending_rate: {
    label: "What a loan costs",
    whoFor: "banks and licensed lenders",
    matters:
      "The one field where disclosure is near-complete, and only because Bank of Ghana requires it and publishes the result. Left to themselves, almost no Ghanaian lender publishes a rate.",
  },
};

export const revalidate = 3600;

export default async function WhatGetsPublishedPage() {
  const fields = await getDisclosure();
  const totalRecords = fields.reduce((n, f) => n + f.total, 0);
  const totalPublished = fields.reduce((n, f) => n + f.published, 0);

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
          The disclosure record
        </p>
        <h1
          className="mt-2 text-[2rem] font-bold leading-[1.1] sm:text-[2.4rem]"
          style={{
            fontFamily: "var(--font-display)",
            letterSpacing: "-0.02em",
          }}
        >
          What gets published, and what doesn&rsquo;t
        </h1>
        <p
          className="mt-5 text-[16.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          Every other page here reports what Ghanaian providers publish. This
          one reports what they do not — which is most of it, and which is
          harder to establish than it sounds.
        </p>
        <p
          className="mt-4 text-[15.5px] leading-relaxed"
          style={{ color: C.muted }}
        >
          Anyone can find a figure that exists. Showing that one does not
          requires going to every licensed firm, finding nothing, and recording
          that nothing was found, on a date. We have {totalRecords} such
          records, and {totalPublished} of them found something.
        </p>

        {/* The counts. This is the finding; the names below are the credit. */}
        <div className="mt-8 space-y-4">
          {fields.map((f) => {
            const meta = FIELDS[f.field] ?? {
              label: f.field,
              whoFor: "providers",
              matters: "",
            };
            const pct = f.total ? (f.published / f.total) * 100 : 0;
            const none = f.published === 0;
            const all = f.published === f.total;

            return (
              <section
                key={f.field}
                className="overflow-hidden rounded-2xl"
                style={{ background: C.card, border: `1px solid ${C.rule}` }}
              >
                <div className="p-5">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <h2 className="text-[15px] font-bold">{meta.label}</h2>
                    <span
                      className="text-[1.3rem] font-bold tabular-nums"
                      style={{
                        color: all ? C.good : none ? C.clay : C.ink,
                      }}
                    >
                      {f.published}
                      <span
                        className="ml-1 text-[13px] font-semibold"
                        style={{ color: C.muted }}
                      >
                        of {f.total} publish it
                      </span>
                    </span>
                  </div>

                  <div
                    className="mt-3 h-1.5 w-full overflow-hidden rounded-full"
                    style={{ background: C.rule }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.max(pct, pct > 0 ? 1.5 : 0)}%`,
                        background: all ? C.good : C.gold,
                      }}
                    />
                  </div>

                  <p
                    className="mt-3 text-[13.5px] leading-relaxed"
                    style={{ color: C.muted }}
                  >
                    Across Ghana&rsquo;s {meta.whoFor}. {meta.matters}
                  </p>

                  {/* Named because they publish. We do not list the rest —
                      the same data as a list of who does not would be an
                      accusation, and unfair to a firm nobody has asked. */}
                  {f.publishers.length > 0 && (
                    <div
                      className="mt-4 rounded-xl p-3.5"
                      style={{ background: "#F2FAF6", border: `1px solid ${C.good}33` }}
                    >
                      <p
                        className="text-[10.5px] font-semibold uppercase tracking-[0.12em]"
                        style={{ color: C.good }}
                      >
                        Published by
                      </p>
                      <p className="mt-1.5 text-[13px] leading-relaxed">
                        {f.publishers.map((p, i) => (
                          <span key={p.slug + i}>
                            {i > 0 && ", "}
                            <Link
                              href={`/providers/${p.slug}`}
                              className="underline underline-offset-4"
                              style={{ color: C.deep }}
                            >
                              {p.name}
                            </Link>
                          </span>
                        ))}
                      </p>
                    </div>
                  )}

                  {none && (
                    <p
                      className="mt-4 text-[13px] leading-relaxed"
                      style={{ color: C.clay }}
                    >
                      Nobody. Not one licensed firm in this category publishes
                      it, which is why the comparison pages show a blank rather
                      than a figure.
                    </p>
                  )}
                </div>
              </section>
            );
          })}
        </div>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          What a blank means here
        </h2>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          <strong>Not that the firm refused.</strong> Most have never been
          asked by anybody, and a provider that has not published a charge has
          not withheld one — it has simply never been expected to.
        </p>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          <strong>And not that the figure does not exist.</strong> Every fund
          has a charge and every broker has a commission. They are quoted when
          you ask, on the phone or in a branch. What is missing is the ability
          to compare before you are in the room, which is the whole of the
          difference.
        </p>

        <h2
          className="mt-12 text-[1.5rem] font-bold"
          style={{ fontFamily: "var(--font-display)" }}
        >
          How this was established
        </h2>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          Provider by provider, from the registers the Securities and Exchange
          Commission and Bank of Ghana publish. We visit each firm&rsquo;s own
          material, record what it states, and record the date we looked. Where
          nothing is stated, that is what goes in — not an estimate, not a
          figure from elsewhere, and not a blank that might mean we never
          checked.
        </p>
        <p className="mt-3 text-[15.5px] leading-relaxed">
          The record is updated as providers publish. If a firm below moves
          from silence to disclosure, this page moves with it.
        </p>

        <div
          className="mt-6 rounded-2xl p-5"
          style={{ background: "#FFF8EC", border: `1px solid ${C.gold}` }}
        >
          <p className="text-[14px] font-bold">If you work at one of these firms</p>
          <p
            className="mt-2 text-[13.5px] leading-relaxed"
            style={{ color: C.muted }}
          >
            Send us your charges, your minimum, or what somebody abroad needs
            to open an account, and it goes on your page here — cited, dated,
            free, and whether or not it flatters you. We publish what providers
            send because a comparison built on what is public is only as good
            as what has been made public.
          </p>
          <p className="mt-2.5 text-[13px]">
            <a
              href={`mailto:${BRAND.dataEmail}`}
              className="font-semibold underline underline-offset-4"
              style={{ color: C.deep }}
            >
              {BRAND.dataEmail}
            </a>
          </p>
        </div>

        <DataProvenance
          title="Disclosure by Ghanaian licensed financial providers"
          source="Provider websites and published material, checked against the SEC and Bank of Ghana registers"
          covering={`${totalRecords} provider-field records`}
          checked="September 2026"
          method="One record per provider per field. A record with no publication date and a recent check date means we looked and found nothing — not that the provider refused, and not that the figure does not exist."
          pageUrl="https://cedafin.com/what-gets-published"
        />

        <p className="mt-6 text-[12.5px]" style={{ color: C.muted }}>
          {BRAND.legalStatus}
        </p>
      </div>

      <Footer />
    </main>
  );
}
