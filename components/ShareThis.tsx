"use client";

import { useState } from "react";

/**
 * components/ShareThis.tsx — the half that was missing.
 *
 * The pages carry a data card in their metadata, so a shared link shows the
 * figure rather than a bare URL. That only helps if somebody shares, and
 * nothing on the site asked anyone to.
 *
 * WHY WHATSAPP AND A COPY LINK, AND NOTHING ELSE
 * WhatsApp because that is how things move in Ghana. Copy because it covers
 * every other case without a row of buttons nobody presses. Facebook and X
 * buttons are clutter here — the audience is not there and the icons make a
 * page look like a blog from 2014.
 *
 * WHY IT PROMPTS RATHER THAN JUST SITTING THERE
 * A button provides; a line of text asks. Asking works better, and the honest
 * version of the ask names who the thing is FOR — "somebody about to borrow"
 * rather than "your network". One prompt per page, at the point where a reader
 * has just learned something, not floating in a corner throughout.
 *
 * NO COUNTS, NO TRACKING
 * No share counter, no analytics on the click. A counter showing zero is worse
 * than no counter, and this site tells providers to publish what they can
 * prove — it should not quietly log what readers do.
 */

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  bg: "#F2F6F9",
  rule: "#DAE4EB",
  muted: "#5F6E78",
  wa: "#25D366",
  good: "#0E8F62",
};

export default function ShareThis({
  /** Absolute path on this site, e.g. "/funding". */
  path,
  /** Who this is for — "somebody about to borrow". Names the recipient. */
  audience,
  /** The text that travels with the link. Should carry the finding itself. */
  message,
}: {
  path: string;
  audience: string;
  message: string;
}) {
  const [copied, setCopied] = useState(false);
  const url = `https://cedafin.com${path}`;
  const wa = `https://wa.me/?text=${encodeURIComponent(`${message} ${url}`)}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div
      className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-2.5 rounded-2xl p-4"
      style={{ background: C.bg, border: `1px solid ${C.rule}` }}
    >
      <p className="text-[13.5px] leading-relaxed" style={{ color: C.ink }}>
        Know {audience}? Send it to them.
      </p>

      <div className="flex gap-2">
        <a
          href={wa}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-[12.5px] font-semibold text-white transition-opacity hover:opacity-90"
          style={{ background: C.wa }}
        >
          {/* Inline so there is no icon library for two buttons. */}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M17.5 14.4c-.3-.1-1.8-.9-2-1s-.5-.1-.7.1-.8 1-.9 1.2-.3.2-.6.1a8 8 0 0 1-2.4-1.5 9 9 0 0 1-1.6-2c-.2-.3 0-.5.1-.6l.5-.5.3-.5v-.5l-1-2.2c-.2-.5-.4-.5-.6-.5h-.6c-.2 0-.5.1-.8.4a3 3 0 0 0-1 2.2 5.3 5.3 0 0 0 1.1 2.8 12 12 0 0 0 4.7 4.1c.7.3 1.2.5 1.6.6a3.9 3.9 0 0 0 1.8.1c.5-.1 1.7-.7 2-1.4s.3-1.2.2-1.3zM12 2a10 10 0 0 0-8.6 15L2 22l5.2-1.4A10 10 0 1 0 12 2zm0 18.3a8.3 8.3 0 0 1-4.2-1.2l-.3-.2-3 .8.8-3-.2-.3A8.3 8.3 0 1 1 12 20.3z" />
          </svg>
          WhatsApp
        </a>

        <button
          type="button"
          onClick={copy}
          className="rounded-full px-3.5 py-2 text-[12.5px] font-semibold transition-colors"
          style={
            copied
              ? { background: C.good, color: "#fff" }
              : { background: "#fff", color: C.deep, border: `1px solid ${C.rule}` }
          }
        >
          {copied ? "Link copied" : "Copy link"}
        </button>
      </div>
    </div>
  );
}
