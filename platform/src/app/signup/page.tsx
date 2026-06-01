import Link from "next/link";
import { signup } from "@/app/auth/actions";

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-2xl font-extrabold">
          GEO<span className="text-accent">·</span>Platform
        </h1>
        <p className="mb-6 text-sm text-dim">Create your agency workspace.</p>

        {error && (
          <div className="mb-4 rounded-md border border-critical/50 bg-critical/10 px-3 py-2 text-sm text-poor">
            {error}
          </div>
        )}

        <form action={signup} className="space-y-3">
          <input
            name="org"
            type="text"
            required
            placeholder="Agency / company name"
            className="w-full rounded-md border border-line bg-navy px-3 py-2 text-sm outline-none focus:border-link"
          />
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
            minLength={6}
            placeholder="Password (min 6 chars)"
            className="w-full rounded-md border border-line bg-navy px-3 py-2 text-sm outline-none focus:border-link"
          />
          <button className="w-full rounded-md bg-blue py-2 text-sm font-semibold text-white hover:opacity-90">
            Create workspace
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-dim">
          Already have an account?{" "}
          <Link href="/login" className="text-link">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
