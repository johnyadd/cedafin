import { NextResponse } from "next/server";

import { getSiteCounts } from "@/lib/data/funds";

/**
 * /api/counts — every count the site shows, from the one place they are
 * defined. The consistency check reads this and compares it with what the
 * pages actually say; anybody else can read it to see what the site believes.
 */
export const revalidate = 3600;

export async function GET() {
  return NextResponse.json(await getSiteCounts());
}
