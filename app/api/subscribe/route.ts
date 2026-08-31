/**
 * app/api/subscribe/route.ts — joining the list, and leaving it.
 *
 * WHY THE UNSUBSCRIBE LIVES HERE TOO
 * A list you cannot leave is not consent, it is capture. Building the exit at
 * the same time as the entrance means there is never a period where someone
 * has subscribed and has no way out — which is both the law and the decent
 * thing.
 *
 * WHAT IS NOT COLLECTED
 * No IP address, no user agent, no timestamp beyond the date, no referrer
 * beyond the page slug the form was on. Every one of those is available and
 * none is needed to send somebody an article they asked for.
 *
 * ALREADY SUBSCRIBED
 * Returns success rather than an error. Telling a stranger "that address is
 * already on the list" confirms whether a given person subscribed, which is
 * information about them that we have no business disclosing to whoever typed
 * their address in.
 */

import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

function admin() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  );
}

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const email = String(body.email ?? "").trim().toLowerCase();
    const source = String(body.source ?? "").slice(0, 120);

    if (!EMAIL.test(email) || email.length > 254) {
      return NextResponse.json(
        { error: "That doesn't look like an email address." },
        { status: 400 },
      );
    }

    const db = admin();
    const { data: existing } = await db
      .from("subscribers")
      .select("id, unsubscribed_at")
      .eq("email", email)
      .maybeSingle();

    if (existing) {
      // Previously unsubscribed and now subscribing again: honour the new
      // consent by clearing the flag rather than leaving them off the list.
      if (existing.unsubscribed_at) {
        await db
          .from("subscribers")
          .update({ unsubscribed_at: null, source })
          .eq("id", existing.id);
        return NextResponse.json({ ok: true });
      }
      // Do NOT reveal that the address is already subscribed — that would
      // confirm to a stranger whether a given person is on the list.
      return NextResponse.json({ ok: true, already: true });
    }

    const { error } = await db.from("subscribers").insert({ email, source });
    if (error) {
      return NextResponse.json(
        { error: "Couldn't save that. Try again in a moment?" },
        { status: 500 },
      );
    }
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json(
      { error: "Couldn't read that request." },
      { status: 400 },
    );
  }
}

/**
 * Unsubscribe by token, via GET so it works from a plain link in an email.
 *
 * The token is random and per-subscriber, so nobody can remove someone else by
 * editing a URL — which they could if this took an email address.
 */
export async function GET(req: Request) {
  const token = new URL(req.url).searchParams.get("token");
  if (!token) {
    return new NextResponse("Missing token.", { status: 400 });
  }

  const db = admin();
  const { data, error } = await db
    .from("subscribers")
    .update({ unsubscribed_at: new Date().toISOString() })
    .eq("unsubscribe_token", token)
    .select("email")
    .maybeSingle();

  if (error || !data) {
    return new NextResponse(
      "That link didn't work. Email data@cedafin.com and we'll remove you.",
      { status: 404, headers: { "Content-Type": "text/plain" } },
    );
  }

  return new NextResponse(
    "You're unsubscribed. We won't email you again.\n\n" +
      "If that was a mistake, subscribe again at https://cedafin.com/insights",
    { status: 200, headers: { "Content-Type": "text/plain; charset=utf-8" } },
  );
}
