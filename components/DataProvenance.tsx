"use client";

import { useState } from "react";

/**
 * components/DataProvenance.tsx — what this data is, and how to cite it.
 *
 * WHY THIS EXISTS
 * Every page here already says where its figures come from, somewhere in the
 * prose. That is enough for a reader deciding whether to trust us, and not
 * enough for a journalist deciding whether to quote us.
 *
 * A reporter who has to compose an attribution writes "according to a
 * website". One handed a formatted line uses the formatted line. The
 * difference costs us nothing and is the whole gap between being read and
 * being cited — and a citation is worth more than a hundred readers, because
 * it brings a link and the readers of somebody else's masthead.
 *
 * WHAT IT DELIBERATELY IS NOT
 * A licence. The press page says every figure is free to use without
 * permission, credit or notice. A block headed "terms" would contradict that
 * and give a reporter on deadline a reason to look elsewhere. This offers a
 * citation; it does not ask for one.
 *
 * THE DATE THAT MATTERS
 * Two dates, because they answer different questions. "Covering" is the period
 * the figures describe. "Checked" is when our extraction last ran. A reader
 * quoting May 2026 figures we fetched in September needs both, and conflating
 * them is how stale data gets published as current.
 */

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  bg: "#F2F6F9",
  muted: "#5F6E78",
  gold: "#E8A33D",
  teal: "#1B8BC0",
};

export default function DataProvenance({
  title,
  source,
  sourceUrl,
  covering,
  checked,
  method,
  pageUrl,
}: {
  /** What the dataset is, in a few words. */
  title: string;
  /** Who published the underlying figures. */
  source: string;
  /** Where they published them, if there is a page to point at. */
  sourceUrl?: string;
  /** The period the figures describe — not when we fetched them. */
  covering: string;
  /** When our extraction last ran. */
  checked: string;
  /** One line on how the figures were derived, where that is not obvious. */
  method?: string;
  /** Absolute URL of this page, for the citation line. */
  pageUrl: string;
}) {
  const [copied, setCopied] = useState(false);

  const citation = `${title}, ${covering}. Compiled by Cedafin from ${source}. ${pageUrl} (accessed ${new Date().toLocaleDateString(
    "en-GB",
    { day: "numeric", month: "long", year: "numeric" },
  )}).`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(citation);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Clipboard access can be refused; the text is selectable either way.
      setCopied(false);
    }
  }

  return (
    <section
      className="mt-8 overflow-hidden rounded-2xl"
      style={{ background: C.card, border: `1px solid ${C.rule}` }}
    >
      {/* Coloured header, matching the section bars elsewhere on the site.
          Grey on white read as a footnote, which is the opposite of what this
          block is for. */}
      <div
        className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-5 py-3"
        style={{ background: `linear-gradient(90deg, ${C.deep}, ${C.teal})` }}
      >
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-white">
          About this data
        </p>
        <p className="text-[11.5px] text-white opacity-80">
          Free to quote &middot; no permission needed
        </p>
      </div>

      <div className="p-5">
        <dl className="grid gap-x-6 gap-y-2.5 text-[13px] sm:grid-cols-[auto_1fr]">
          <dt className="font-semibold" style={{ color: C.muted }}>
            Source
          </dt>
          <dd>
            {sourceUrl ? (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-4"
                style={{ color: C.deep }}
              >
                {source}
              </a>
            ) : (
              source
            )}
          </dd>

          {/* Two dates, because they answer different questions and
              conflating them is how stale figures get quoted as current. */}
          <dt className="font-semibold" style={{ color: C.muted }}>
            Covering
          </dt>
          <dd>{covering}</dd>

          <dt className="font-semibold" style={{ color: C.muted }}>
            Last checked
          </dt>
          <dd>{checked}</dd>

          {method && (
            <>
              <dt className="font-semibold" style={{ color: C.muted }}>
                Method
              </dt>
              <dd style={{ color: C.muted }}>{method}</dd>
            </>
          )}
        </dl>

        {/* The point of the whole component. */}
        <div
          className="mt-4 rounded-xl p-4"
          style={{ background: "#FFF8EC", border: `1px solid ${C.gold}` }}
        >
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p
              className="text-[10.5px] font-semibold uppercase tracking-[0.12em]"
              style={{ color: C.muted }}
            >
              Cite this
            </p>
            <button
              type="button"
              onClick={copy}
              className="rounded-full px-3 py-1 text-[11.5px] font-semibold transition-colors"
              style={
                copied
                  ? { background: "#0E8F62", color: "#fff" }
                  : { background: C.deep, color: "#fff" }
              }
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <p
            className="mt-2 text-[12.5px] leading-relaxed"
            style={{ color: C.ink }}
          >
            {citation}
          </p>
        </div>

        <p className="mt-3 text-[12px] leading-relaxed" style={{ color: C.muted }}>
          Use any of this without asking. No permission needed, no credit
          required — the line above is offered because a formatted citation is
          easier than composing one, not because we ask for it.
        </p>
      </div>
    </section>
  );
}
