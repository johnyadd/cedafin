/**
 * lib/compliance/licence-status.ts
 *
 * The SEC licensee register carries a status classification per licensee. It is
 * the single most valuable trust signal available — and the single most likely
 * way this product attracts a defamation claim.
 *
 * The Commission has stated publicly that it has NOT issued any list of fund
 * management firms that are unsafe to invest with; that the classification only
 * indicates licensees with regulatory issues or unresolved complaints (some
 * suspended, some having voluntarily surrendered licences, others at various
 * stages of resolving complaints); and that it is inaccurate and wrong to
 * universally categorise those flagged as companies that are not safe to
 * invest in.
 *
 * THEREFORE, in every rendered surface:
 *   - status text comes from this map, VERBATIM — never paraphrased, never
 *     model-generated, never summarised
 *   - never rendered as "unsafe", "avoid", "warning", "risky", or "danger"
 *   - always accompanied by the register link and the date checked
 *   - never drives a TrustScore penalty that reads as a safety verdict; a
 *     flagged licensee simply scores lower on "licence verified and current",
 *     which is a factual component, not a judgement
 *
 * Enforced by the CI compliance check: any licence-status string appearing in
 * rendered output must match a `display` value below exactly.
 *
 * See ARCHITECTURE.md §17.3.
 */

export const SEC_REGISTER_URL = "https://licensees.sec.gov.gh/";

export type LicenceStatusKey =
  | "in_good_standing"
  | "regulatory_issues"
  | "suspended"
  | "voluntarily_surrendered"
  | "revoked"
  | "not_found"
  | "unverified";

export interface LicenceStatusDisplay {
  key: LicenceStatusKey;
  /** Rendered VERBATIM. Do not edit without checking the register's own wording. */
  display: string;
  /** Neutral explanatory line. Also verbatim. */
  detail: string;
  /**
   * Visual treatment. Deliberately excludes any danger styling — no red, no
   * warning iconography. "attention" is amber and means "read this", not
   * "avoid this".
   */
  tone: "neutral" | "positive" | "attention";
  /** Whether products from this provider remain listed. Listing != endorsement. */
  listProducts: boolean;
  /** Points contributed to the TrustScore licence component (max 30). */
  trustPoints: number;
}

export const LICENCE_STATUS: Record<LicenceStatusKey, LicenceStatusDisplay> = {
  in_good_standing: {
    key: "in_good_standing",
    display: "Licensed by the SEC, Ghana",
    detail:
      "This entity appears on the SEC's register of licensed operators with no classification noted.",
    tone: "positive",
    listProducts: true,
    trustPoints: 30,
  },
  regulatory_issues: {
    key: "regulatory_issues",
    display: "Licensed — the SEC register notes regulatory issues requiring attention",
    detail:
      "The SEC has stated that this classification indicates licensees with various regulatory issues or unresolved complaints, and that it should not be read as a list of firms that are unsafe to invest with. Check the register for this licensee's current status.",
    tone: "attention",
    listProducts: true,
    trustPoints: 10,
  },
  suspended: {
    key: "suspended",
    display: "Suspended from the market by the SEC",
    detail:
      "The SEC register records this licensee as suspended. Check the register for the current position before taking any action.",
    tone: "attention",
    listProducts: false,
    trustPoints: 0,
  },
  voluntarily_surrendered: {
    key: "voluntarily_surrendered",
    display: "Licence voluntarily surrendered",
    detail:
      "The SEC register records that this licensee voluntarily surrendered its licence.",
    tone: "attention",
    listProducts: false,
    trustPoints: 0,
  },
  revoked: {
    key: "revoked",
    display: "Licence revoked by the SEC",
    detail:
      "The SEC has published a notice revoking this licence. Retained here as a historical record.",
    tone: "attention",
    listProducts: false,
    trustPoints: 0,
  },
  not_found: {
    key: "not_found",
    display: "Not found on the SEC register",
    detail:
      "We could not locate this entity on the SEC's register of licensed operators on the date checked. This may mean it is not licensed, or that it is listed under a different legal name.",
    tone: "attention",
    listProducts: false,
    trustPoints: 0,
  },
  unverified: {
    key: "unverified",
    display: "Licence status not yet checked",
    detail: "We have not yet verified this entity against the SEC register.",
    tone: "neutral",
    listProducts: false,
    trustPoints: 0,
  },
};

/** Every string that may legitimately appear in rendered output. CI asserts this. */
export const ALLOWED_STATUS_STRINGS: readonly string[] = Object.values(LICENCE_STATUS)
  .flatMap((s) => [s.display, s.detail]);

/** Phrases that must NEVER appear adjacent to a provider name. CI asserts this. */
export const FORBIDDEN_STATUS_PHRASES = [
  "unsafe", "not safe", "avoid", "scam", "fraudulent", "dangerous",
  "do not invest", "blacklist", "warning:", "risky provider",
] as const;

/**
 * Every rendered status must carry provenance. Returns null when the status has
 * not been verified — callers show nothing rather than guessing.
 */
export function renderLicenceStatus(
  key: LicenceStatusKey | null | undefined,
  verifiedOn: string | null | undefined,
): { display: string; detail: string; tone: string; verifiedOn: string; sourceUrl: string } | null {
  if (!key || !verifiedOn) return null;
  const s = LICENCE_STATUS[key];
  if (!s) return null;
  return {
    display: s.display,
    detail: s.detail,
    tone: s.tone,
    verifiedOn,
    sourceUrl: SEC_REGISTER_URL,
  };
}

const total = LICENCE_STATUS.in_good_standing.trustPoints;
if (total !== 30) {
  throw new Error(`Licence component must cap at 30 TrustScore points, got ${total}`);
}
