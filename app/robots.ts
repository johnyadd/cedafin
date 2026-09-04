/**
 * app/robots.ts — what crawlers may read.
 *
 * Everything is public and everything may be indexed, except the API routes,
 * which return JSON that would only clutter results.
 *
 * The sitemap line is the part that matters: it tells a crawler where the
 * full list of pages is rather than leaving it to follow links.
 */

import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: "/api/",
    },
    sitemap: "https://cedafin.com/sitemap.xml",
  };
}
