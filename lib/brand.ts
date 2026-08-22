/**
 * lib/brand.ts — every user-visible mention of the product name.
 *
 * WHY THIS EXISTS: the name is a placeholder. "CediWise" came off the shortlist
 * in the strategy document and got baked into a scaffold script before anyone
 * decided anything. The plan is to name the thing once it is clear what it is,
 * which means a rename is coming.
 *
 * On the previous project that rename left both pre- and post-rebrand copies of
 * most landing components in the repo, plus mojibake in a footer that appeared
 * on every page. None of it was serious; all of it was avoidable.
 *
 * So: NO COMPONENT EVER HARDCODES THE NAME. Everything reads from here, and a
 * rebrand is this file plus a domain purchase.
 *
 * Same principle as lib/scoring/config.ts holding the methodology: one source of
 * truth, and the places that display it derive from it rather than repeat it.
 */

export const BRAND = {
  /** Display name. Provisional. */
  name: "CediWise",

  /** Used where the name appears mid-sentence. */
  nameLower: "CediWise",

  /**
   * The positioning in one line. Earns its place in the title tag and the
   * header, so it should say what the product does, not what it aspires to.
   */
  tagline: "Before you invest, compare.",

  /**
   * One sentence for meta descriptions and the provider outreach email.
   * Deliberately factual: this is a comparison site, not an adviser, and the
   * compliance boundary in lib/compliance/boundary.ts depends on that framing
   * holding everywhere the product describes itself.
   */
  description:
    "Independent comparison of regulated Ghanaian investment funds — fees, " +
    "returns after inflation, and access terms, every figure traced to the " +
    "document it came from.",

  /** Not yet registered. Update together with the deployed domain. */
  domain: "cediwise.com",
  url: "https://cediwise.com",

  contactEmail: "hello@cediwise.com",
  dataEmail: "data@cediwise.com",

  /**
   * Rendered in the footer beside the disclaimer. States what the product is
   * NOT, which matters more than what it is while COMPLIANCE_PHASE is 1 or 2.
   */
  legalStatus:
    "Not licensed by the Securities and Exchange Commission of Ghana. " +
    "We publish factual comparisons of regulated products and do not provide " +
    "investment advice, hold client money, or execute transactions.",

  launchYear: 2026,
} as const;

/** Page titles. Keeps the separator and ordering consistent across the site. */
export function pageTitle(page?: string): string {
  return page ? `${page} · ${BRAND.name}` : `${BRAND.name} — ${BRAND.tagline}`;
}

/** Footer copyright. Built from launchYear so it never goes stale by hand. */
export function copyright(): string {
  const now = new Date().getFullYear();
  const span = now > BRAND.launchYear ? `${BRAND.launchYear}–${now}` : `${now}`;
  // Escaped codepoint, not a pasted glyph: a pasted © arrived as mojibake on
  // every page of the previous project and went unnoticed for weeks.
  return `\u00A9 ${span} ${BRAND.name}`;
}
