/**
 * components/AdSlot.tsx — sponsor placement, on articles only.
 *
 * WHERE THIS MAY AND MAY NOT APPEAR
 * Articles. Not comparison pages, not the matching flows, not the broker or
 * shares listings.
 *
 * The reason is the site's only real asset. Every page says some version of
 * the same thing: we publish what providers disclose, we take no money from
 * them, the ranking is neutral. A Stanbic banner beside the page ranking
 * Stanbic against First Atlantic destroys that in one glance, whether or not
 * a cedi changed hands over the ordering. Readers are not wrong to assume the
 * worst — most comparison sites in richer markets do exactly that.
 *
 * Articles are different. A reader knows an article is a piece of writing with
 * a sponsor, the way a newspaper column is. That is a normal arrangement and
 * it does not touch the figures.
 *
 * WHY IT RENDERS NOTHING WHEN EMPTY
 * The obvious thing is a dotted box saying "Advertise here". On a site with no
 * traffic that announces two things to a prospective sponsor: nobody is buying,
 * and we are keen. Both weaken the position. Until a sponsor exists the
 * component returns null and the page is simply shorter.
 *
 * WHY THE LABEL IS NOT NEGOTIABLE
 * "Sponsored" appears above every placement, in the same weight as any other
 * heading. A sponsor asking for it to be softened is asking the site to blur
 * the line it exists to hold, and the answer is no — which is easier to say
 * when the label is structural rather than a choice made per deal.
 */

import Link from "next/link";

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  gold: "#E8A33D",
  rule: "#DAE4EB",
  muted: "#5F6E78",
  card: "#FFFFFF",
};

export interface Sponsor {
  name: string;
  /** One or two sentences. Their words, not ours. */
  copy: string;
  href: string;
  cta: string;
}

/**
 * Live sponsors, keyed by placement. Empty until someone buys one.
 *
 * Kept as a constant rather than a database table for the same reason the
 * articles are files: there are none yet, and building an admin screen for an
 * empty list is work spent on the wrong end.
 */
const SPONSORS: Record<string, Sponsor | undefined> = {
  // "article-mid": {
  //   name: "Example Asset Management",
  //   copy: "…",
  //   href: "https://example.com",
  //   cta: "Read more",
  // },
};

export default function AdSlot({ placement }: { placement: string }) {
  const s = SPONSORS[placement];
  if (!s) return null;

  return (
    <aside
      className="my-8 rounded-2xl p-5"
      style={{ background: C.card, border: `1px solid ${C.rule}` }}
    >
      <p
        className="text-[10.5px] font-semibold uppercase tracking-[0.16em]"
        style={{ color: C.gold }}
      >
        Sponsored
      </p>
      <p className="mt-2 text-[14px] font-bold" style={{ color: C.ink }}>
        {s.name}
      </p>
      <p className="mt-1 text-[13.5px] leading-relaxed" style={{ color: C.muted }}>
        {s.copy}
      </p>
      <p className="mt-3 text-[13px] font-semibold">
        <a
          href={s.href}
          target="_blank"
          rel="noopener noreferrer sponsored"
          className="underline underline-offset-4"
          style={{ color: C.deep }}
        >
          {s.cta} →
        </a>
      </p>
      {/*
        Said on every placement, not buried in a policy page. A reader who
        wonders whether the sponsor influenced the article should find the
        answer next to the sponsor.
      */}
      <p className="mt-3 text-[11px]" style={{ color: C.muted }}>
        Sponsors pay for placement beside articles. They see no copy before
        publication, and no sponsor has ever affected a figure, a ranking or a
        comparison on this site.{" "}
        <Link
          href="/insights"
          className="underline underline-offset-2"
          style={{ color: C.deep }}
        >
          How this works
        </Link>
      </p>
    </aside>
  );
}
