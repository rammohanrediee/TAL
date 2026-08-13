export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-5 py-8 text-ink sm:px-8">
      <section className="w-full max-w-xl rounded-2xl border border-border bg-surface p-6 shadow-xl shadow-zinc-500/10 sm:px-12 sm:py-10">
        {/* Page heading */}
        <header className="mb-8">
          <p className="mb-3 text-xl font-bold tracking-tight text-action">
            TAL
          </p>

          <h1 className="text-3xl font-semibold text-ink">
            Welcome back
          </h1>

          <p className="mt-2 text-sm text-ink-muted">
            Sign in to continue your job search.
          </p>
        </header>

        {/* Google login */}
        <a
          href="/backend/api/v1/auth/google/login"
          className="flex min-h-11 w-full items-center justify-center gap-3 rounded-[10px] border border-border px-4 py-3 font-medium text-ink transition-colors hover:border-border-strong hover:bg-surface-subtle"
        >
          <span aria-hidden="true" className="font-bold text-blue-600">
            G
          </span>

          Continue with Google
        </a>

        {/* Divider */}
        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-border" />

          <span className="text-xs uppercase tracking-wide text-ink-muted">
            Or continue with email
          </span>

          <div className="h-px flex-1 bg-border" />
        </div>

        {/* Email login form */}
        <form className="space-y-5">
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium text-ink"
            >
              Email address
            </label>

            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              placeholder="you@example.com"
              className="min-h-11 w-full rounded-[10px] border border-border bg-canvas px-3 py-3 text-ink outline-none placeholder:text-ink-muted focus:border-action focus:ring-2 focus:ring-action/20"
            />
          </div>
        </form>
      </section>
    </main>
  );
}
