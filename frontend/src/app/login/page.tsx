export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-5 py-8 text-foreground sm:px-8">
      <section className="w-full max-w-xl rounded-2xl border border-border bg-surface p-6 shadow-xl shadow-zinc-500/10 sm:px-12 sm:py-10">
        {/* Page heading */}
        <header className="mb-8">
          <p className="mb-3 text-xl font-bold tracking-tight text-accent">
            TAL
          </p>

          <h1 className="text-3xl font-semibold text-foreground">
            Welcome back
          </h1>

          <p className="mt-2 text-sm text-muted">
            Sign in to continue your job search.
          </p>
        </header>

        {/* Google login */}
        <a
          href="http://127.0.0.1:8000/api/v1/auth/google/login"
          className="flex w-full items-center justify-center gap-3 rounded-lg border border-border px-4 py-3 font-medium text-foreground transition-colors hover:bg-surface-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          <span aria-hidden="true" className="font-bold text-blue-600">
            G
          </span>

          Continue with Google
        </a>

        {/* Divider */}
        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-border" />

          <span className="text-xs uppercase tracking-wide text-muted">
            Or continue with email
          </span>

          <div className="h-px flex-1 bg-border" />
        </div>

        {/* Email login form */}
        <form className="space-y-5">
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium text-foreground"
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
              className="w-full rounded-lg border border-border bg-input px-3 py-3 text-foreground outline-none placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
          </div>
        </form>
      </section>
    </main>
  );
}
