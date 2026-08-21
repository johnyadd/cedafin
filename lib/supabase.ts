/**
 * lib/supabase.ts — client factories.
 *
 * TWO CLIENTS, AND THE DIFFERENCE MATTERS:
 *
 *   publicClient()  — anon key, RLS enforced. Reads published rows only.
 *                     Use for every public page.
 *   adminClient()   — service role key, RLS BYPASSED. Use ONLY in server
 *                     routes for ingestion, approval, score runs and admin.
 *                     Never import this into a client component. The service
 *                     key must never reach the browser.
 *
 * RLS GOTCHA carried over from Finanyst: a write blocked by a MISSING policy
 * affects zero rows and returns NO error — indistinguishable from a write that
 * legitimately matched nothing. Be suspicious of any operation that can
 * succeed at zero rows; assert the returned count. Write all four policies
 * (select/insert/update/delete) when you create a table.
 */

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { env, publicEnv } from "./env";

/** Anon key, RLS enforced. Safe on any surface. */
export function publicClient(): SupabaseClient {
  return createClient(
    publicEnv.NEXT_PUBLIC_SUPABASE_URL,
    publicEnv.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    { auth: { persistSession: false } },
  );
}

/** Service role, RLS bypassed. Server routes only — never a client component. */
export function adminClient(): SupabaseClient {
  if (typeof window !== "undefined") {
    throw new Error("adminClient() called in the browser — service key would leak");
  }
  return createClient(env.NEXT_PUBLIC_SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

/**
 * Assert a write actually affected rows.
 *
 *   const { data } = await admin.from("products").update({...}).eq("id", id).select();
 *   assertAffected(data, 1, "publish product");
 *
 * Without this, a missing RLS policy looks exactly like success.
 */
export function assertAffected(
  rows: unknown[] | null,
  expected: number,
  operation: string,
): void {
  const n = rows?.length ?? 0;
  if (n !== expected) {
    throw new Error(
      `${operation}: expected ${expected} row(s), affected ${n}. ` +
        `Check the RLS policy for this table and command.`,
    );
  }
}
