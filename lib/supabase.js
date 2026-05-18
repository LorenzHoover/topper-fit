import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

// Browser-safe client — uses anon key, respects Row Level Security.
// Use this in Client Components and for read-only public queries.
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Server-only client — uses service_role key, bypasses RLS.
// Only call this from API routes or Server Components, never in browser code.
// The service_role key is NOT prefixed with NEXT_PUBLIC_ so it never reaches the browser.
export function createServiceClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY
  )
}
