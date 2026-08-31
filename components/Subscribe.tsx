/**
 * components/Subscribe.tsx — the one thing on this site that compounds.
 *
 * WHY AN EMAIL LIST AND NOT A SHARE BUTTON
 * A visitor who reads an article and leaves is worth nothing. One who
 * subscribes can be reached again, and the list is the asset that makes
 * everything else possible later — sponsorship, a newsletter, an audience to
 * point at when a fund manager asks who reads this.
 *
 * WHAT THE FORM PROMISES, AND WHY IT SAYS IT
 * "A note when we publish something." Not "insights", not "exclusive market
 * intelligence", not a weekly cadence we have no intention of keeping. The
 * site's whole argument is that it says what it can prove; a subscribe box
 * that oversells is the same failure in miniature.
 *
 * CONSENT IS NOT A FOOTNOTE
 * The operator is UK-based (UK GDPR) and the readers are largely Ghanaian
 * (Data Protection Act 2012). Both need consent, a stated purpose and a way
 * out. So the form states what will be sent, how often, that the address is
 * used for nothing else, and that one click ends it — above the button, not in
 * grey type below it.
 *
 * NO TRACKING
 * No opens, no clicks, no pixel. A site that tells providers to publish what
 * they can prove should not quietly log whether a reader opened an email.
 */

"use client";

import { useState } from "react";

const C = {
  ink: "#0C1C22",
  deep: "#0B4F6C",
  teal: "#1B8BC0",
  gold: "#E8A33D",
  clay: "#C0492B",
  bg: "#F2F6F9",
  card: "#FFFFFF",
  rule: "#DAE4EB",
  muted: "#5F6E78",
  good: "#0E8F62",
};

export default function Subscribe({
  source,
  compact = false,
}: {
  /** Which page this was submitted from — recorded as evidence of consent. */
  source: string;
  /** Narrower styling for a sidebar. */
  compact?: boolean;
}) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "done" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");

  async function submit() {
    if (!email.includes("@") || email.length < 5) {
      setState("error");
      setMessage("That doesn't look like an email address.");
      return;
    }
    setState("sending");
    try {
      const r = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), source }),
      });
      const data = await r.json();
      if (!r.ok) {
        setState("error");
        setMessage(data.error ?? "Something went wrong. Try again?");
        return;
      }
      setState("done");
      setMessage(
        data.already
          ? "You're already on the list."
          : "Done. We'll write when there's something worth reading.",
      );
    } catch {
      setState("error");
      setMessage("Couldn't reach us. Try again in a moment?");
    }
  }

  if (state === "done") {
    return (
      <div
        className="rounded-2xl p-5"
        style={{ background: C.card, border: `1px solid ${C.good}` }}
      >
        <p className="text-[14px] font-bold" style={{ color: C.good }}>
          {message}
        </p>
      </div>
    );
  }

  return (
    <section
      className={compact ? "rounded-2xl p-4" : "rounded-2xl p-5 sm:p-6"}
      style={{ background: C.card, border: `1px solid ${C.gold}` }}
    >
      <h2 className={compact ? "text-[13.5px] font-bold" : "text-[16px] font-bold"}>
        Get the next one
      </h2>
      <p
        className={`mt-2 leading-relaxed ${compact ? "text-[11.5px]" : "text-[13.5px]"}`}
        style={{ color: C.muted }}
      >
        {/*
          Says what it is, not what it could be sold as. We publish
          irregularly and there is no honest way to promise a schedule.
        */}
        A note when we publish something — what the numbers show about Ghanaian
        funds, credit, gold and shares. Irregular, because we write when we find
        something rather than to a schedule.
      </p>

      <div className={compact ? "mt-3" : "mt-4 flex flex-wrap gap-2"}>
        <input
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (state === "error") setState("idle");
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
          }}
          className={`rounded-full px-4 py-2.5 text-[13.5px] ${
            compact ? "w-full" : "min-w-[14rem] flex-1"
          }`}
          style={{ border: `1px solid ${C.rule}`, background: C.bg }}
        />
        <button
          type="button"
          onClick={submit}
          disabled={state === "sending"}
          className={`cursor-pointer rounded-full px-5 py-2.5 text-[13.5px] font-bold ${
            compact ? "mt-2 w-full" : ""
          }`}
          style={{
            background: C.gold,
            color: C.ink,
            opacity: state === "sending" ? 0.6 : 1,
          }}
        >
          {state === "sending" ? "One moment…" : "Subscribe"}
        </button>
      </div>

      {state === "error" && (
        <p className="mt-2 text-[12.5px]" style={{ color: C.clay }}>
          {message}
        </p>
      )}

      {/*
        Above the fold of the box, not buried beneath it. Someone typing their
        address deserves to know what happens to it before they press the
        button, not after.
      */}
      <p
        className={`mt-3 leading-relaxed ${compact ? "text-[10.5px]" : "text-[11.5px]"}`}
        style={{ color: C.muted }}
      >
        Your address is used to send you these and nothing else. Never sold,
        never shared, and one click unsubscribes. We don&rsquo;t track whether
        you open anything.
      </p>
    </section>
  );
}
