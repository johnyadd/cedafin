import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Analytics from "@/components/Analytics";
import SiteHeader from "@/components/SiteHeader";
import Ticker from "@/components/Ticker";
import { BRAND } from "@/lib/brand";
import { getTicker } from "@/lib/data/funds";
import { getArticles } from "@/lib/insights";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Cedafin — what Ghanaian savings and credit actually cost",
    template: "%s · Cedafin",
  },
  description:
    "Fund charges, Treasury bill rates, bank lending APRs, gold and listed " +
    "shares in Ghana — from the documents providers publish themselves. " +
    "Every figure dated and sourced.",
  metadataBase: new URL("https://cedafin.com"),
};

/*
  Header and ticker live here rather than on each page. Two reasons: every
  page then has the same navigation, and the ticker keeps scrolling across a
  page change instead of restarting each time — which it did when it was
  mounted per page.
*/
export const revalidate = 3600;

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const [ticker, articles] = await Promise.all([
    getTicker(),
    Promise.resolve(getArticles()),
  ]);

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <SiteHeader
          name={BRAND.name}
          articles={articles.slice(0, 4).map((a) => ({
            slug: a.slug,
            title: a.title,
          }))}
        />
        <Ticker items={ticker} />
        {children}
        <Analytics />
      </body>
    </html>
  );
}
