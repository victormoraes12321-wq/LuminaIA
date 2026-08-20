import { redirect } from 'next/navigation'

// ── Root Route — Redirect to Dashboard ────────────────────────

export default function Home() {
  redirect('/dashboard')
}
