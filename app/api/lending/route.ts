/**
 * app/api/lending/route.ts — bank lending rates, for the funding match flow.
 *
 * Same reasoning as /api/funds: the match page runs in the browser so that
 * trading history, turnover and what the money is for never reach a server.
 * With a named contact attached that is personal data under Ghana's Data
 * Protection Act, and commercially sensitive besides. Data goes out, answers
 * do not come back.
 *
 * WHAT IS SENT, AND WHAT IS NOT THERE TO SEND
 * Provider, category, tenor, lending rate, APR, and the gap between the last
 * two. No minimum, no maximum, no security requirement, no eligibility, no
 * turnaround — because Bank of Ghana's APR report contains none of those, and
 * a check of 24 bank websites found none published either. The match page says
 * so rather than quietly filtering on nothing.
 */

import { NextResponse } from "next/server";

import { getLending } from "@/lib/data/funds";

export const revalidate = 3600;

export async function GET() {
  try {
    const rows = await getLending();

    return NextResponse.json(
      rows.map((r) => ({
        id: r.id,
        slug: r.slug,
        name: r.name,
        provider: r.provider.name,
        providerSlug: r.provider.slug,
        category: r.category,
        tenorYears: r.tenorYears,
        lendingRatePct: r.lendingRatePct,
        aprPct: r.aprPct,
        // The difference between what a bank advertises and what it costs.
        // Agricultural Development Bank lends at 19.59% and charges 28.13%;
        // Access Bank's gap is 0.03. Ranking on the advertised rate would put
        // them in the wrong order, which is the whole reason this is sent.
        feeGapPct: r.feeGapPct,
      })),
    );
  } catch {
    return NextResponse.json(
      { error: "Could not load lenders right now." },
      { status: 500 },
    );
  }
}
