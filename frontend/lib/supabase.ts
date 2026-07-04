import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// Supabase is used for AUTH ONLY. All product data flows
// Frontend → FastAPI backend → Supabase; the anon key never reads app tables
// from the client. Lazy singleton so importing this module never throws at
// build/prerender time when env vars are absent.
let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient {
  if (!client) {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (!url || !key) {
      throw new Error(
        "Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY."
      );
    }
    client = createClient(url, key);
  }
  return client;
}

export async function getAccessToken(): Promise<string | null> {
  const { data } = await getSupabase().auth.getSession();
  return data.session?.access_token ?? null;
}
