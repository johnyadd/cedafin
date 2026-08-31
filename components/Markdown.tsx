/**
 * components/Markdown.tsx — enough markdown for the writing this site does.
 *
 * WHAT IT HANDLES
 * Headings, paragraphs, bullet and numbered lists, tables, bold, italic,
 * inline code, links, blockquotes and horizontal rules. That covers every
 * article this site has needed so far, and tables matter more here than in
 * most blogs — a piece about what gold costs is mostly figures.
 *
 * WHAT IT DOES NOT
 * Images, footnotes, nested lists, code blocks with syntax highlighting, HTML
 * passthrough. If an article needs one of those, that is the signal to install
 * a real markdown library rather than to add another case here. A parser that
 * grows one special case at a time becomes the thing nobody dares touch.
 *
 * WHY NOT dangerouslySetInnerHTML
 * The obvious shortcut is to build an HTML string and inject it. Article
 * content is written by us, so the injection risk is low — but "low" is not a
 * standard, and a site that lectures providers about rigour should not take
 * shortcuts it would criticise. Everything below returns React elements.
 */

import Link from "next/link";
import { Fragment, type ReactNode } from "react";

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  gold: "#E8A33D",
  rule: "#DAE4EB",
  muted: "#5F6E78",
  bg: "#F2F6F9",
};

/** Bold, italic, inline code and links, inside a line of text. */
function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  const rx =
    /(\*\*[^*]+\*\*)|(\*[^*]+\*)|(`[^`]+`)|(\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;

  while ((m = rx.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    const k = `${keyBase}-${i++}`;

    if (tok.startsWith("**")) {
      out.push(<strong key={k}>{tok.slice(2, -2)}</strong>);
    } else if (tok.startsWith("`")) {
      out.push(
        <code
          key={k}
          className="rounded px-1 py-0.5 text-[0.9em]"
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
        out.push(
          internal ? (
            <Link
              key={k}
              href={href}
              className="underline underline-offset-4"
              style={{ color: C.deep }}
            >
              {label}
            </Link>
          ) : (
            <a
              key={k}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-4"
              style={{ color: C.deep }}
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

function Table({ rows }: { rows: string[] }) {
  const cells = rows.map((r) =>
    r
      .replace(/^\||\|$/g, "")
      .split("|")
      .map((c) => c.trim()),
  );
  // Row two is the |---|---| separator; it carries alignment we ignore.
  const head = cells[0];
  const body = cells.slice(2);

  return (
    <div className="my-6 overflow-x-auto">
      <table className="w-full border-collapse text-[13.5px]">
        <thead>
          <tr>
            {head.map((h, i) => (
              <th
                key={i}
                className="border-b-2 px-3 py-2 text-left font-semibold"
                style={{ borderColor: C.rule }}
              >
                {inline(h, `th-${i}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, r) => (
            <tr key={r}>
              {row.map((c, i) => (
                <td
                  key={i}
                  className="border-b px-3 py-2 tabular-nums"
                  style={{ borderColor: C.rule }}
                >
                  {inline(c, `td-${r}-${i}`)}
                </td>
              ))}
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

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i++;
      continue;
    }

    // Table: a pipe row followed by a separator row.
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
      const sizes = ["text-[26px]", "text-[21px]", "text-[17px]", "text-[15px]"];
      const Tag = (["h1", "h2", "h3", "h4"] as const)[level - 1];
      out.push(
        <Tag
          key={key++}
          className={`mt-8 mb-3 font-bold leading-tight ${sizes[level - 1]}`}
          style={{ color: C.ink }}
        >
          {inline(text, `h-${key}`)}
        </Tag>,
      );
      i++;
      continue;
    }

    if (/^(---|\*\*\*)\s*$/.test(line.trim())) {
      out.push(
        <hr key={key++} className="my-8" style={{ borderColor: C.rule }} />,
      );
      i++;
      continue;
    }

    if (line.trim().startsWith(">")) {
      const quote: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quote.push(lines[i].replace(/^\s*>\s?/, ""));
        i++;
      }
      out.push(
        <blockquote
          key={key++}
          className="my-6 border-l-4 pl-4 text-[15px] italic"
          style={{ borderColor: C.gold, color: C.muted }}
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
          className={`my-4 space-y-2 pl-6 text-[15px] leading-relaxed ${
            ordered ? "list-decimal" : "list-disc"
          }`}
        >
          {items.map((it, n) => (
            <li key={n}>{inline(it, `li-${key}-${n}`)}</li>
          ))}
        </List>,
      );
      continue;
    }

    // Paragraph: consecutive non-blank lines that are not something else.
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
    out.push(
      <p key={key++} className="my-4 text-[15px] leading-relaxed">
        {inline(para.join(" "), `p-${key}`)}
      </p>,
    );
  }

  return <Fragment>{out}</Fragment>;
}
