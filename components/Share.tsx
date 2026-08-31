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
  gold: "#E8A33D",
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

  // Each platform's own colour. Recognisable at a glance, which a row of
  // identical grey pills is not — and WhatsApp leads because that is how
  // things actually circulate in Ghana.
  const links: [label: string, href: string, colour: string][] = [
    ["WhatsApp", `https://wa.me/?text=${text}`, "#25D366"],
    [
      "LinkedIn",
      `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
      "#0A66C2",
    ],
    ["X", `https://twitter.com/intent/tweet?text=${text}`, "#000000"],
    [
      "Email",
      `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(url)}`,
      C.deep,
    ],
  ];

  return (
    <section className="mt-8">
      <p
        className="text-[11px] font-semibold uppercase tracking-[0.14em]"
        style={{ color: C.gold }}
      >
        Share this
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {links.map(([label, href, colour]) => (
          <a
            key={label}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full px-4 py-2.5 text-[12.5px] font-bold text-white transition-opacity hover:opacity-85"
            style={{ background: colour }}
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
          className="cursor-pointer rounded-full px-4 py-2.5 text-[12.5px] font-bold transition-colors"
          style={{
            background: copied ? C.deep : C.card,
            color: copied ? "#FFFFFF" : C.ink,
            border: `1px solid ${copied ? C.deep : C.rule}`,
          }}
        >
          {copied ? "Copied" : "Copy link"}
        </button>
      </div>
    </section>
  );
}
