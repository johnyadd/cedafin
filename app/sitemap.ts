/**
 * app/sitemap.ts — what exists, for crawlers.
 *
 * WHY THIS MATTERS MORE THAN IT LOOKS
 * Without a sitemap a search engine finds pages only by following links. That
 * works eventually, but "eventually" for a new site with no inbound links can
 * be months — and the comparison pages, lender pages and provider pages are
 * generated from data rather than linked from a menu, so some may never be
 * reached at all.
 *
 * WHY IT READS FROM THE DATABASE
 * Twenty-three lender pages, six comparison groups, five providers and a
 * growing list of articles. Hand-listing them means the sitemap is wrong the
 * first time anything changes, and a sitemap listing pages that no longer
 * exist is worse than none.
 *
 * PRIORITIES AND FREQUENCIES ARE HONEST
 * The comparison pages change when the data does — daily for gold, weekly for
 * bills, rarely for fund charges. Articles change almost never once published.
 * Saying "daily" for everything is a lie search engines have long since
 * learned to ignore.
 */

import type { MetadataRoute } from "next";

import { getLenderSlugs, getPeerGroups } from "@/lib/data/funds";
import { getArticles } from "@/lib/insights";

const BASE = "https://cedafin.com";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  // Spread through .map() widens the literal frequency strings to plain
  // string, which the type rejects. Written out instead.
  const fixed: MetadataRoute.Sitemap = [
    { url: BASE, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${BASE}/funds`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${BASE}/shares`, lastModified: now, changeFrequency: "daily", priority: 0.9 },
    { url: `${BASE}/brokers`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE}/funding`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${BASE}/calculator`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE}/inflation-calculator`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE}/loan-calculator`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE}/match`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${BASE}/funding/match`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${BASE}/insights`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${BASE}/methodology`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${BASE}/work-with-us`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
  ];

  const [groups, lenders, articles] = await Promise.all([
    getPeerGroups(),
    getLenderSlugs(),
    Promise.resolve(getArticles()),
  ]);

  const compare: MetadataRoute.Sitemap = groups.map((g) => ({
    url: `${BASE}/compare/${g.peerGroup.replace(":", "-")}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.8,
  }));

  const lenderPages: MetadataRoute.Sitemap = lenders.map((slug) => ({
    url: `${BASE}/lenders/${slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  // Articles carry their own date, so lastModified is real rather than "now".
  const insights: MetadataRoute.Sitemap = articles.map((a) => ({
    url: `${BASE}/insights/${a.slug}`,
    lastModified: new Date(`${a.date}T00:00:00Z`),
    changeFrequency: "yearly",
    priority: 0.7,
  }));

  return [...fixed, ...compare, ...lenderPages, ...insights];
}
