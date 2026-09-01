/**
 * components/Markdown.tsx — article typography.
 *
 * WHY THIS WAS RESTYLED
 * The first version rendered correct markup at 15px with no measure control,
 * so lines ran the full container width and every paragraph carried the same
 * weight. It read like a document rather than something published — which
 * matters, because a reader deciding whether to trust figures about their
 * money is partly deciding whether this looks like a serious publication.
 *
 * WHAT CHANGED AND WHY
 *
 *   Size — 17px, up from 15. Below about 16px sustained reading gets tiring,
 *   and these pieces are four minutes long.
 *
 *   Measure — capped at 68 characters. Unconstrained lines force the eye to
 *   hunt for the start of the next one, which is the single most common
 *   typographic failure on the web.
 *
 *   Tables — these articles are mostly figures, so tables are the main visual
 *   element rather than an afterthought. Right-aligned numerals, tabular
 *   figures so digits line up in columns, zebra striping, and the last column
 *   emphasised because in every table here it carries the finding.
 *
 *   Headings — Fraunces at a larger size with real space above, so a reader
 *   scanning can find the structure without reading.
 *
 *   Blockquotes — set as pull quotes rather than indented text, because in
 *   these pieces a quote is always the sentence that carries the point.
 *
 * WHAT IT STILL DOES NOT HANDLE
 * Images, footnotes, nested lists, code blocks. If an article needs one, that
 * is the signal to install a real markdown library rather than add another
 * case here.
 */

import Link from "next/link";
import { Fragment, type ReactNode } from "react";

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  teal: "#1B8BC0",
  gold: "#E8A33D",
  clay: "#C0492B",
  rule: "#DAE4EB",
  muted: "#5F6E78",
  bg: "#F2F6F9",
  card: "#FFFFFF",
};

/** Bold, italic, inline code and links, within a line of text. */
function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  const rx = /(\*\*[^*]+\*\*)|(\*[^*]+\*)|(`[^`]+`)|(\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;

  while ((m = rx.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    const k = `${keyBase}-${i++}`;

    if (tok.startsWith("**")) {
      out.push(
        <strong key={k} style={{ color: C.ink, fontWeight: 700 }}>
          {tok.slice(2, -2)}
        </strong>,
      );
    } else if (tok.startsWith("`")) {
      out.push(
        <code
          key={k}
          className="rounded px-1.5 py-0.5 text-[0.88em] tabular-nums"
          style={{ background: C.bg }}
        >
          {tok.slice(1, -1)}
        </code>,
      );
    } else if (tok.startsWith("[")) {
      const lm = tok.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (lm) {
        const [, label, href] = lm;
        const internal = href.startsWith("/");
        const style = {
          color: C.deep,
          textDecorationColor: C.gold,
          textUnderlineOffset: "3px",
          textDecorationThickness: "1.5px",
        };
        out.push(
          internal ? (
            <Link key={k} href={href} className="underline" style={style}>
              {label}
            </Link>
          ) : (
            <a
              key={k}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
              style={style}
            >
              {label}
            </a>
          ),
        );
      } else {
        out.push(tok);
      }
    } else {
      out.push(<em key={k}>{tok.slice(1, -1)}</em>);
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

/**
 * These articles are mostly figures, so the table is the main visual element.
 * Numbers right-aligned and tabular so digits line up down a column; the last
 * column emphasised because in every table on this site it carries the point.
 */
function Table({ rows }: { rows: string[] }) {
  const cells = rows.map((r) =>
    r
      .replace(/^\||\|$/g, "")
      .split("|")
      .map((c) => c.trim()),
  );
  const head = cells[0];

  /*
    A row wrapped in ** is the point of the table.

    The renderer cannot know which figure matters — 7.75% is only remarkable
    beside 3.46%, and no rule derives that. So the article says so, by bolding
    the first cell of the row that carries the finding, and it is set apart
    here. Marking it in the source keeps the editorial judgement where it
    belongs: with whoever wrote the piece.
  */
  const body = cells.slice(2).map((row) => {
    const marked = /^\*\*.*\*\*$/.test(row[0]);
    return {
      cells: marked ? [row[0].replace(/^\*\*|\*\*$/g, ""), ...row.slice(1)] : row,
      marked,
    };
  });

  const isNum = (v: string) =>
    /^[+\-−]?[\d,.]+\s*%?$/.test(v.replace(/GH₵|GH¢/g, "").trim());

  return (
    <div className="my-8 overflow-x-auto">
      <table
        className="w-full border-collapse overflow-hidden rounded-xl text-[14px]"
        style={{ background: C.card, border: `1px solid ${C.rule}` }}
      >
        {/* Deep blue header — frames it as a data table rather than text. */}
        <thead>
          <tr
            style={{
              background: `linear-gradient(135deg, ${C.deep} 0%, ${C.teal} 90%)`,
            }}
          >
            {head.map((h, i) => (
              <th
                key={i}
                className={`px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-white ${
                  i === 0 ? "text-left" : "text-right"
                }`}
              >
                {inline(h, `th-${i}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, r) => (
            <tr
              key={r}
              style={{
                background: row.marked
                  ? "rgba(232,163,61,0.13)"
                  : r % 2
                    ? C.bg
                    : C.card,
              }}
            >
              {row.cells.map((c, i) => {
                const lastCol = i === row.cells.length - 1 && row.cells.length > 2;
                return (
                  <td
                    key={i}
                    className={`px-4 py-3 ${
                      i === 0 ? "text-left" : "text-right tabular-nums"
                    } ${lastCol || row.marked ? "font-bold" : ""}`}
                    style={{
                      borderBottom:
                        r === body.length - 1 ? "none" : `1px solid ${C.rule}`,
                      borderLeft:
                        row.marked && i === 0 ? `3px solid ${C.gold}` : "none",
                      // The finding column in the brand blue, so the eye lands
                      // on the number the table exists to show.
                      color: lastCol && isNum(c) ? C.deep : C.ink,
                      fontSize: lastCol ? "15px" : undefined,
                    }}
                  >
                    {inline(c, `td-${r}-${i}`)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Markdown({ body }: { body: string }) {
  const lines = body.split(/\r?\n/);
  const out: ReactNode[] = [];
  let i = 0;
  let key = 0;
  let firstPara = true;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i++;
      continue;
    }

    if (line.trim().startsWith("|") && lines[i + 1]?.includes("---")) {
      const rows: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        rows.push(lines[i]);
        i++;
      }
      out.push(<Table key={key++} rows={rows} />);
      continue;
    }

    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      const level = h[1].length;
      const text = h[2];
      const Tag = (["h1", "h2", "h3", "h4"] as const)[level - 1];
      const size = ["2rem", "1.6rem", "1.25rem", "1.05rem"][level - 1];

      /*
        A numbered h3 — "### 1. Money market funds" — gets the number set as a
        marker rather than run into the text. In a guide the numbers are the
        structure, and a reader scanning for step three should find it without
        reading the words around it.
      */
      const numbered = level === 3 ? text.match(/^(\d+)\.\s+(.*)$/) : null;

      if (numbered) {
        out.push(
          <h3
            key={key++}
            className="mt-14 mb-4 flex items-baseline gap-3"
            style={{ fontFamily: "var(--font-display)" }}
          >
            <span
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[16px] font-bold text-white"
              style={{ background: C.deep }}
            >
              {numbered[1]}
            </span>
            <span
              className="text-[1.35rem] font-bold leading-[1.2]"
              style={{ color: C.ink, letterSpacing: "-0.01em" }}
            >
              {inline(numbered[2], `h-${key}`)}
            </span>
          </h3>,
        );
        i++;
        continue;
      }

      // h2 in a long piece carries a rule above it, so sections read as
      // sections rather than as bolder paragraphs.
      out.push(
        <Tag
          key={key++}
          className={
            level === 2 ? "mt-14 mb-4 border-t pt-8 font-bold leading-[1.15]"
                        : "mt-12 mb-4 font-bold leading-[1.2]"
          }
          style={{
            fontFamily: "var(--font-display)",
            fontSize: size,
            color: C.ink,
            letterSpacing: "-0.015em",
            borderColor: level === 2 ? C.rule : undefined,
          }}
        >
          {inline(text, `h-${key}`)}
        </Tag>,
      );
      i++;
      continue;
    }

    if (/^(---|\*\*\*)\s*$/.test(line.trim())) {
      out.push(
        <hr
          key={key++}
          className="mx-auto my-10 w-16"
          style={{ borderColor: C.gold, borderTopWidth: "2px" }}
        />,
      );
      i++;
      continue;
    }

    // Set as a pull quote, not indented text — in these pieces a quote is
    // always the sentence carrying the point.
    if (line.trim().startsWith(">")) {
      const quote: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quote.push(lines[i].replace(/^\s*>\s?/, ""));
        i++;
      }
      out.push(
        <blockquote
          key={key++}
          className="my-9 border-l-[3px] py-1 pl-6 text-[19px] leading-[1.5]"
          style={{
            borderColor: C.gold,
            color: C.ink,
            fontFamily: "var(--font-display)",
          }}
        >
          {inline(quote.join(" "), `q-${key}`)}
        </blockquote>,
      );
      continue;
    }

    const bullet = /^\s*[-*]\s+/;
    const numbered = /^\s*\d+\.\s+/;
    if (bullet.test(line) || numbered.test(line)) {
      const ordered = numbered.test(line);
      const items: string[] = [];
      const rx = ordered ? numbered : bullet;
      while (i < lines.length && rx.test(lines[i])) {
        items.push(lines[i].replace(rx, ""));
        i++;
      }
      const List = ordered ? "ol" : "ul";
      out.push(
        <List
          key={key++}
          className={`my-6 space-y-2.5 pl-6 text-[17px] leading-[1.65] ${
            ordered ? "list-decimal" : "list-disc"
          }`}
          style={{ maxWidth: "68ch", color: C.ink }}
        >
          {items.map((it, n) => (
            <li key={n} className="pl-1.5">
              {inline(it, `li-${key}-${n}`)}
            </li>
          ))}
        </List>,
      );
      continue;
    }

    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].match(/^#{1,4}\s/) &&
      !lines[i].trim().startsWith(">") &&
      !lines[i].trim().startsWith("|") &&
      !bullet.test(lines[i]) &&
      !numbered.test(lines[i])
    ) {
      para.push(lines[i]);
      i++;
    }

    // The opening paragraph is set larger. A reader deciding whether to
    // continue reads this one, and nothing else on the page competes with it.
    const lead = firstPara;
    firstPara = false;
    const text = para.join(" ");

    /*
      A paragraph that OPENS with bold is a labelled point — "**What it
      costs.** An annual charge…" — and in a guide those carry the structure
      within a section. Given a tinted panel and a gold edge they can be found
      by scanning, which is how anyone actually reads a guide this long.
    */
    const labelled = !lead && /^\*\*[^*]+\.\*\*\s/.test(text);

    out.push(
      <p
        key={key++}
        className={
          lead
            ? "mb-7 text-[20px] leading-[1.55]"
            : labelled
              ? "my-5 rounded-r-xl border-l-[3px] py-3 pl-4 pr-4 text-[16.5px] leading-[1.65]"
              : "my-6 text-[17px] leading-[1.7]"
        }
        style={{
          maxWidth: "68ch",
          color: C.ink,
          fontWeight: lead ? 500 : 400,
          borderColor: labelled ? C.gold : undefined,
          background: labelled ? "rgba(232,163,61,0.07)" : undefined,
        }}
      >
        {inline(text, `p-${key}`)}
      </p>,
    );
  }

  return <Fragment>{out}</Fragment>;
}
