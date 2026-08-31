/**
 * components/Share.tsx — passing it on.
 *
 * WHY THESE AND NOT A WIDGET
 * Plain links, no third-party script. The usual share widgets load code from
 * another company that then knows every page every visitor reads, whether or
 * not anyone clicks. On a site that tells providers to publish what they can
 * prove, quietly handing a reader's browsing to a third party would be hard to
 * defend.
 *
 * WHY WHATSAPP IS FIRST
 * It is how things actually circulate in Ghana. A share row that leads with
 * X and LinkedIn is designed for a different country.
 *
 * WHY COPY-LINK EXISTS
 * Most sharing is invisible — pasted into a message, an email, a group. The
 * button that costs nothing to include is the one people use most.
 */

"use client";

import { useState } from "react";

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  rule: "#DAE4EB",
  muted: "#5F6E78",
  card: "#FFFFFF",
};

export default function Share({
  title,
  slug,
}: {
  title: string;
  slug: string;
}) {
  const [copied, setCopied] = useState(false);
  const url = `https://cedafin.com/insights/${slug}`;
  const text = encodeURIComponent(`${title} — ${url}`);

  const links: [string, string][] = [
    ["WhatsApp", `https://wa.me/?text=${text}`],
    [
      "LinkedIn",
      `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
    ],
    ["X", `https://twitter.com/intent/tweet?text=${text}`],
    [
      "Email",
      `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(url)}`,
    ],
  ];

  return (
    <section className="mt-8">
      <p
        className="text-[11px] font-semibold uppercase tracking-[0.14em]"
        style={{ color: C.muted }}
      >
        Share this
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {links.map(([label, href]) => (
          <a
            key={label}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full px-4 py-2 text-[12.5px] font-semibold"
            style={{
              background: C.card,
              color: C.ink,
              border: `1px solid ${C.rule}`,
            }}
          >
            {label}
          </a>
        ))}
        <button
          type="button"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(url);
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            } catch {
              /* clipboard blocked — the other buttons still work */
            }
          }}
          className="cursor-pointer rounded-full px-4 py-2 text-[12.5px] font-semibold"
          style={{
            background: C.card,
            color: copied ? C.deep : C.ink,
            border: `1px solid ${copied ? C.deep : C.rule}`,
          }}
        >
          {copied ? "Copied" : "Copy link"}
        </button>
      </div>
    </section>
  );
}
