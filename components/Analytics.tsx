/**
 * components/Analytics.tsx — page views, and nothing that contradicts the
 * promise the match pages make.
 *
 * WHAT THIS SENDS AND WHAT IT DOES NOT
 * Page views and standard Google Analytics parameters: which URL, referrer,
 * device, approximate location. That is all. There are no custom events, and
 * in particular nothing is fired from the matching flows.
 *
 * That restraint is deliberate. /match tells a visitor in its banner that
 * their answers stay in the browser and nothing is saved or sent. Firing an
 * event when someone selects "GH¢100 to 1,000" or "65 or over" would make that
 * banner a lie — the data would leave the browser, to Google, attached to a
 * client identifier. Knowing which answers people give would be genuinely
 * useful for improving the questions. It is not worth breaking a promise the
 * page makes in its first line.
 *
 * IP ANONYMISATION
 * Set explicitly. GA4 does this by default, but a default can change and this
 * cannot silently become more invasive than intended.
 *
 * GHANA'S DATA PROTECTION ACT
 * Analytics identifiers are personal data under the Act, which requires a
 * lawful basis. Most Ghanaian sites load trackers without asking. This one
 * says so in the footer rather than pretending it doesn't — the same standard
 * it holds providers to about disclosure.
 */

"use client";

import Script from "next/script";

const GA_ID = "G-Y75J886EVQ";

export default function Analytics() {
  // Nothing loads outside production, so a developer working locally does not
  // pollute the property with their own page views.
  if (process.env.NODE_ENV !== "production") return null;

  return (
    <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
        strategy="afterInteractive"
      />
      <Script id="ga-init" strategy="afterInteractive">
        {`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', '${GA_ID}', {
            anonymize_ip: true,
            allow_google_signals: false,
            allow_ad_personalization_signals: false
          });
        `}
      </Script>
    </>
  );
}
