/**
 * components/SiteHeader.tsx — navigation across the whole site.
 *
 * WHY DROPDOWNS RATHER THAN A FLAT ROW
 * There are now fourteen destinations: funds, five comparison groups, shares,
 * brokers, two matching flows, lending, insights. A flat row of fourteen links
 * is unreadable, and the alternative this site has used so far — each page
 * linking to whatever seemed relevant — left the matching flows unreachable
 * for a day and nearly did the same to brokers and shares.
 *
 * Grouped under four headings, every page is two clicks from anywhere and a
 * new page that is missing from the menu is obvious.
 *
 * WHY IT IS A CLIENT COMPONENT
 * The menus open on hover on a desktop and on tap on a phone, which needs
 * state. Nothing else here does.
 */

"use client";

import Link from "next/link";
import { useState } from "react";

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  teal: "#1B8BC0",
  gold: "#E8A33D",
  rule: "#DAE4EB",
  muted: "#5F6E78",
  card: "#FFFFFF",
};

type Item = [href: string, label: string, note?: string];

const MENUS: { label: string; items: Item[] }[] = [
  {
    label: "Invest",
    items: [
      ["/funds", "Every fund", "75 catalogued, charges compared"],
      ["/compare/money_market-GHS", "Money market funds"],
      ["/compare/fixed_income-GHS", "Fixed income funds"],
      ["/compare/balanced-GHS", "Balanced funds"],
      ["/compare/government_security-GHS", "Treasury bills"],
      // Also listed under "Shares & gold". Duplicated deliberately: someone
      // looking to invest expects shares in the Invest menu, and the
      // distinction between a single company and a diversified fund is worth
      // keeping visible without making shares hard to find.
      ["/shares", "Listed shares", "39 companies on the exchange"],
      // Gold sits here too. It is a commodity rather than a capital market
      // product, which is why it has its own menu — but people search for it
      // as an investment, and someone browsing Invest will not think to look
      // under "Shares & gold" for it.
      ["/compare/commodity-GHS", "Gold", "Coins and the NewGold ETF"],
      ["/calculator", "Return calculator", "What the fund did, what the currency did"],
      ["/match", "Find what fits you", "Eight questions, nothing saved"],
    ],
  },
  {
    label: "Shares & gold",
    items: [
      ["/shares", "Listed shares", "39 companies, price history"],
      ["/compare/equity-GHS", "Compare shares"],
      ["/brokers", "Stockbrokers", "24 firms, none publishes a rate"],
      ["/compare/commodity-GHS", "Gold", "Coins and the NewGold ETF"],
    ],
  },
  {
    label: "Borrow",
    items: [
      ["/funding", "Business credit", "22 banks, real APRs"],
      ["/funding/match", "Find funding that fits"],
    ],
  },
  {
    label: "Insights",
    items: [["/insights", "All articles", "What the numbers show"]],
  },
];

export default function SiteHeader({
  name,
  articles = [],
}: {
  name: string;
  /*
    The three or four most recent, passed in from the server. Capped
    deliberately: four articles in a menu is helpful, forty is a wall, and a
    menu that grows without limit is one nobody maintains.
  */
  articles?: { slug: string; title: string }[];
}) {
  const [open, setOpen] = useState<string | null>(null);
  const [mobile, setMobile] = useState(false);

  return (
    <header
      className="sticky top-0 z-50 border-b"
      style={{ background: C.card, borderColor: C.rule }}
    >
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-5 py-3 sm:px-8">
        <Link
          href="/"
          className="text-[19px] font-bold tracking-tight"
          style={{ color: C.deep }}
        >
          {name}
        </Link>

        <nav className="ml-auto hidden items-center gap-1 lg:flex">
          {MENUS.map((m) => (
            <div
              key={m.label}
              className="relative"
              onMouseEnter={() => setOpen(m.label)}
              onMouseLeave={() => setOpen(null)}
            >
              <button
                type="button"
                onClick={() => setOpen(open === m.label ? null : m.label)}
                className="cursor-pointer rounded-full px-3.5 py-2 text-[13.5px] font-semibold"
                style={{
                  color: open === m.label ? C.deep : C.ink,
                  background: open === m.label ? "#EAF3F8" : "transparent",
                }}
              >
                {m.label}
                <span className="ml-1 text-[10px]">▾</span>
              </button>

              {open === m.label && (
                <div
                  className="absolute right-0 top-full w-80 rounded-2xl p-2 shadow-lg"
                  style={{ background: C.card, border: `1px solid ${C.rule}` }}
                >
                  {m.label === "Insights" &&
                    articles.slice(0, 4).map((a) => (
                      <Link
                        key={a.slug}
                        href={`/insights/${a.slug}`}
                        className="block rounded-xl px-3 py-2.5 hover:bg-[#F2F6F9]"
                      >
                        <span className="text-[13px] font-semibold leading-snug">
                          {a.title}
                        </span>
                      </Link>
                    ))}
                  {m.label === "Insights" && articles.length > 0 && (
                    <div
                      className="my-1.5 border-t"
                      style={{ borderColor: C.rule }}
                    />
                  )}
                  {m.items.map(([href, label, note]) => (
                    <Link
                      key={href}
                      href={href}
                      className="block rounded-xl px-3 py-2.5 hover:bg-[#F2F6F9]"
                    >
                      <span className="text-[13.5px] font-semibold">
                        {label}
                      </span>
                      {note && (
                        <span
                          className="mt-0.5 block text-[11.5px]"
                          style={{ color: C.muted }}
                        >
                          {note}
                        </span>
                      )}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>

        <button
          type="button"
          onClick={() => setMobile(!mobile)}
          className="ml-auto cursor-pointer rounded-full px-3 py-2 text-[13px] font-semibold lg:hidden"
          style={{ border: `1px solid ${C.rule}`, color: C.ink }}
        >
          {mobile ? "Close" : "Menu"}
        </button>
      </div>

      {mobile && (
        <div
          className="border-t px-5 pb-4 lg:hidden"
          style={{ borderColor: C.rule }}
        >
          {MENUS.map((m) => (
            <div key={m.label} className="mt-4">
              <p
                className="text-[10.5px] font-semibold uppercase tracking-[0.14em]"
                style={{ color: C.gold }}
              >
                {m.label}
              </p>
              <ul className="mt-2 space-y-1.5">
                {m.items.map(([href, label]) => (
                  <li key={href}>
                    <Link
                      href={href}
                      onClick={() => setMobile(false)}
                      className="text-[14px]"
                      style={{ color: C.ink }}
                    >
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </header>
  );
}
