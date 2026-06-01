import Link from "next/link";
import { login } from "@/app/auth/actions";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; msg?: string }>;
}) {
  const { error, msg } = await searchParams;
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-2xl font-extrabold">
          GEO<span className="text-accent">·</span>Platform
        </h1>
        <p className="mb-6 text-sm text-dim">
          Sign in to your AI-visibility dashboard.
        </p>

        {error && (
          <div className="mb-4 rounded-md border border-critical/50 bg-critical/10 px-3 py-2 text-sm text-poor">
            {error}
          </div>
        )}
        {msg && (
          <div className="mb-4 rounded-md border border-good/50 bg-good/10 px-3 py-2 text-sm text-good">
            {msg}
          </div>
        )}

        <form action={login} className="space-y-3">
          <input
            name="email"
            type="email"
            required
            placeholder="you@agency.com"
            className="w-full rounded-md border border-line bg-navy px-3 py-2 text-sm outline-none focus:border-link"
          />
          <input
            name="password"
            type="password"
            required
            placeholder="Password"
            className="w-full rounded-md border border-line bg-navy px-3 py-2 text-sm outline-none focus:border-link"
          />
          <button className="w-full rounded-md bg-blue py-2 text-sm font-semibold text-white hover:opacity-90">
            Sign in
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-dim">
          No account?{" "}
          <Link href="/signup" className="text-link">
            Create one
          </Link>
        </p>
      </div>
    </main>
  );
}
