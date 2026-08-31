/**
 * lib/insights.ts — articles, from markdown files in the repo.
 *
 * WHY FILES AND NOT A DATABASE TABLE
 * A table would let articles be published without a deploy, but it needs an
 * admin interface with authentication, forms and image handling — a week of
 * work before a single article exists. Files need none of that: write in the
 * editor, commit, push. Version control comes free, so every edit is visible
 * and revertible.
 *
 * The case for a table gets stronger with volume. At one article a fortnight
 * the bottleneck is writing, not deploying. If that changes, articles are text
 * either way and moving them is a small job.
 *
 * WHY NO MARKDOWN LIBRARY
 * gray-matter and a renderer are two dependencies for something this site
 * barely stretches: headings, paragraphs, lists, tables, bold, links. Parsed
 * here in about a hundred lines, which is less code than the configuration
 * those libraries would need — and nothing to keep updated.
 *
 * The parser is deliberately limited. If an article needs something it cannot
 * do, that is a signal to reach for a real library rather than to keep bolting
 * cases onto this one.
 */

import fs from "node:fs";
import path from "node:path";

const DIR = path.join(process.cwd(), "content", "insights");

export interface Article {
  slug: string;
  title: string;
  /** ISO date. Sorted on this, newest first. */
  date: string;
  /** One or two sentences for the index and for search results. */
  summary: string;
  /** Free-text labels — "gold", "brokers", "data". */
  tags: string[];
  /** Where the figures in the piece came from. */
  sources: string[];
  /** Rough minutes, from word count. */
  readingMinutes: number;
  body: string;
}

function parseFrontmatter(raw: string): [Record<string, string[] | string>, string] {
  const m = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!m) return [{}, raw];

  const meta: Record<string, string[] | string> = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = line.match(/^([a-zA-Z_]+):\s*(.*)$/);
    if (!kv) continue;
    const [, key, value] = kv;
    const v = value.trim();
    // [a, b, c] becomes a list; anything else stays a string.
    if (v.startsWith("[") && v.endsWith("]")) {
      meta[key] = v
        .slice(1, -1)
        .split(",")
        .map((s) => s.trim().replace(/^["']|["']$/g, ""))
        .filter(Boolean);
    } else {
      meta[key] = v.replace(/^["']|["']$/g, "");
    }
  }
  return [meta, m[2]];
}

function str(v: string[] | string | undefined, fallback = ""): string {
  if (Array.isArray(v)) return v[0] ?? fallback;
  return v ?? fallback;
}

function list(v: string[] | string | undefined): string[] {
  if (Array.isArray(v)) return v;
  return v ? [v] : [];
}

export function getArticleSlugs(): string[] {
  if (!fs.existsSync(DIR)) return [];
  return fs
    .readdirSync(DIR)
    .filter((f) => f.endsWith(".md"))
    .map((f) => f.replace(/\.md$/, ""));
}

export function getArticle(slug: string): Article | null {
  const file = path.join(DIR, `${slug}.md`);
  if (!fs.existsSync(file)) return null;

  const [meta, body] = parseFrontmatter(fs.readFileSync(file, "utf-8"));
  const words = body.split(/\s+/).filter(Boolean).length;

  return {
    slug,
    title: str(meta.title, slug),
    date: str(meta.date, "1970-01-01"),
    summary: str(meta.summary),
    tags: list(meta.tags),
    sources: list(meta.sources),
    // 220 words a minute, rounded up. Rough by nature; a figure-heavy piece
    // reads slower than prose and this does not know the difference.
    readingMinutes: Math.max(1, Math.round(words / 220)),
    body: body.trim(),
  };
}

export function getArticles(): Article[] {
  return getArticleSlugs()
    .map(getArticle)
    .filter((a): a is Article => a !== null)
    .sort((a, b) => b.date.localeCompare(a.date));
}
