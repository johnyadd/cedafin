/**
 * lib/brand.ts — the only place the site's identity is written down.
 *
 * WHY THIS FILE EXISTS AT ALL
 * The working name changed twice before launch. Had the name been typed into
 * each page, a rename would have meant hunting it across a home page, a fund
 * directory, four comparison pages, two provider page types, a funding page
 * and a lender page — and missing one would have left a stale name in front of
 * a fund manager or a bank. One import, one edit.
 *
 * THE EMAIL IS LOAD-BEARING
 * dataEmail is not decoration. It appears on every provider and lender page
 * beneath an invitation to send us corrections and factsheets, and it is the
 * reply address for outreach to 23 banks and a dozen fund managers. A site
 * that asks providers to write to an address which bounces is worse than one
 * that asks nothing — it wastes their time and spends credibility that took
 * real work to build.
 *
 * So: before any outreach goes out, send a test to this address and confirm it
 * arrives. Deploying with it unrouted is fine; emailing anyone is not.
 *
 * THE LEGAL LINE IS NOT BOILERPLATE
 * We hold no SEC licence and no credit broking licence. Every page carries
 * legalStatus for that reason, and it is written to be true rather than
 * defensive: we publish factual comparisons, we do not advise, hold money,
 * arrange finance, or take payment for placement. If any of that ever stops
 * being true, this string changes before the behaviour does.
 */

export const BRAND = {
  /** Display name, everywhere. */
  name: "Cedafin",

  /** Bare domain — no protocol, for display. */
  domain: "cedafin.com",

  /** Canonical origin, for metadata and absolute links. */
  url: "https://cedafin.com",

  /**
   * Where providers send factsheets, rate cards and corrections.
   * Appears on the home page, both provider page types, and the funding and
   * lender pages. MUST receive mail before any outreach.
   */
  dataEmail: "data@cedafin.com",

  /** General enquiries — readers rather than providers. */
  contactEmail: "hello@cedafin.com",

  /** One line, on every page. Accurate, not defensive. */
  legalStatus:
    "Not licensed by the Securities and Exchange Commission of Ghana. " +
    "We publish factual comparisons of regulated products and do not " +
    "provide investment advice, hold client money, or execute transactions.",

  /** What the site is, in one sentence. Used in metadata. */
  tagline: "Ghana's money market, with the prices shown.",

  description:
    "Compare Ghanaian investment funds on the charges providers actually " +
    "publish, and business credit on the rates Bank of Ghana reports. Every " +
    "figure dated and sourced.",
} as const;

export type Brand = typeof BRAND;
