/**
 * app/api/funds/route.ts — published funds, for the matching flow.
 *
 * The match page runs in the browser, because the answers must not leave it —
 * age, what someone is saving for, how much they hold. That is personal
 * financial data under Ghana's Data Protection Act, and the cleanest way to
 * avoid every obligation that comes with holding it is not to receive it.
 *
 * So the filtering happens client-side, and this route sends the funds down
 * for it to work on. Traffic goes one way: fund data out, no answers back.
 *
 * ONLY WHAT THE MATCH NEEDS. Not the full FundRow — no source documents, no
 * fee histories, no provenance chains. Those matter on a comparison page where
 * someone is checking our working; here they would be kilobytes of unread JSON
 * on every visit.
 */

import { NextResponse } from "next/server";

import { getPublishedFunds } from "@/lib/data/funds";

export const revalidate = 3600;

export async function GET() {
  try {
    const funds = await getPublishedFunds();

    // Share classes collapse to one fund. Stanbic Income Fund Trust returned
    // 38.80% on one class and 15.39% on another with identical fees — a real
    // and important difference on a comparison page, but showing someone two
    // near-identical rows in a shortlist is noise. The main class stands in.
    const unique = [
      ...new Map(
        funds
          .filter((f) => f.shareClass !== "sub")
          .map((f) => [`${f.provider.slug}::${f.name}`, f]),
      ).values(),
    ];

    return NextResponse.json(
      unique.map((f) => ({
        id: f.id,
        slug: f.slug,
        name: f.name,
        provider: f.provider.name,
        assetClass: f.assetClass ?? "",
        currency: f.currency ?? "GHS",
        chargesPct: f.statedChargesPct?.value ?? null,
        minimumGhs: f.minimumGhs?.value ?? null,
        dealingFrequency: f.dealingFrequency ?? null,
        lockInDays: f.lockInDays ?? null,
        headlineReturn: f.headlineReturn
          ? { pct: f.headlineReturn.value, window: f.headlineReturn.window }
          : null,
      })),
    );
  } catch (e) {
    // The page shows this to the visitor, so it says what failed without
    // leaking connection details.
    return NextResponse.json(
      { error: "Could not load funds right now." },
      { status: 500 },
    );
  }
}
