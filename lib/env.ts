/**
 * lib/env.ts — fail-fast environment validation.
 *
 * WHY THIS FILE EXISTS: on the Finanyst build, PYTHON_ENGINE_URL was set to
 * http://localhost:8000 in .env.local, pointing at nothing. The browser showed
 * "Unexpected token '<' is not valid JSON" and two days went into hunting
 * Vercel, middleware, next.config and RLS. Production had been fine the whole
 * time. Six lines of boot-time assertion would have caught it in one second.
 *
 * Import this from any server route that touches Supabase or the engine.
 * Never read process.env directly elsewhere.
 */

import { z } from "zod";

const serverSchema = z.object({
  NEXT_PUBLIC_SUPABASE_URL: z.string().url("must be the full https:// project URL"),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(20, "looks truncated"),
  SUPABASE_SERVICE_ROLE_KEY: z.string().min(20, "looks truncated"),
  ANTHROPIC_API_KEY: z.string().startsWith("sk-ant-", "should start with sk-ant-"),
  PYTHON_ENGINE_URL: z.string().url("must be a full URL, e.g. http://localhost:8000"),
  OUTBOUND_TOKEN_SECRET: z.string().min(32, "use at least 32 random characters"),
  COMPLIANCE_PHASE: z.coerce.number().int().min(1).max(3),
});

const clientSchema = serverSchema.pick({
  NEXT_PUBLIC_SUPABASE_URL: true,
  NEXT_PUBLIC_SUPABASE_ANON_KEY: true,
});

function parse<T extends z.ZodTypeAny>(schema: T, source: unknown, label: string) {
  const result = schema.safeParse(source);
  if (!result.success) {
    const lines = result.error.issues
      .map((i) => `  ${i.path.join(".")}: ${i.message}`)
      .join("\n");
    // Thrown at import time — the app refuses to start rather than failing
    // later with a message that points at the wrong layer.
    throw new Error(`Invalid ${label} environment:\n${lines}\n`);
  }
  return result.data;
}

/** Server-only. Throws at import if anything is missing or malformed. */
export const env = parse(serverSchema, process.env, "server") as z.infer<typeof serverSchema>;

/** Safe to reference from client components. */
export const publicEnv = parse(
  clientSchema,
  {
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  },
  "client",
);

/** Engine health check. Call from /admin/health, not from request paths. */
export async function checkEngine(): Promise<{ ok: boolean; detail: string }> {
  try {
    const res = await fetch(`${env.PYTHON_ENGINE_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return { ok: false, detail: `engine returned ${res.status}` };
    const body = await res.json();
    return { ok: true, detail: `engine_version ${body.engine_version}` };
  } catch (e) {
    return { ok: false, detail: e instanceof Error ? e.message : "unreachable" };
  }
}
