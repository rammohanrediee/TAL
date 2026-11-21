"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");
    if (!email || !password || busy) return;
    setBusy(true);
    setError("");
    try {
      const body = new URLSearchParams({ username: email, password });
      const response = await fetch("/backend/api/v1/auth/token", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      if (response.status === 401) throw new Error("Email or password is incorrect.");
      if (!response.ok) throw new Error("Could not sign in. Please try again.");
      router.replace("/chat");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not sign in. Please try again.");
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-tal-canvas px-5 py-16 text-tal-ink">
      <Link href="/" className="absolute left-6 top-6 flex items-center gap-2 text-xl font-black"><span className="grid size-8 place-items-center rounded-[9px] bg-tal-yellow text-base">T</span>TAL</Link>
      <section className="w-full max-w-md rounded-[18px] border border-tal-border bg-tal-surface p-7 shadow-lg shadow-black/5 sm:p-10">
        <p className="text-xs font-bold text-tal-secondary">TAL / Account</p>
        <h1 className="mt-2 text-4xl font-black tracking-tight">Welcome back.</h1>
        <p className="mt-3 text-sm leading-6 text-tal-secondary">Sign in to see your chats and continue the conversation.</p>
        <a href="/backend/api/v1/auth/google/login" className="mt-8 flex min-h-11 w-full items-center justify-center rounded-[10px] border border-tal-border px-4 text-sm font-bold hover:bg-tal-subtle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-tal-ink">Continue with Google</a>
        <div className="my-6 flex items-center gap-3 text-xs text-tal-muted"><span className="h-px flex-1 bg-tal-border" />or use email<span className="h-px flex-1 bg-tal-border" /></div>
        <form onSubmit={signIn} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-bold">Email address</label>
            <input id="email" name="email" type="email" autoComplete="email" required className="min-h-11 w-full rounded-[10px] border border-tal-border bg-tal-surface px-3 text-sm outline-none focus:border-tal-ink focus:ring-2 focus:ring-tal-yellow" />
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-bold">Password</label>
            <input id="password" name="password" type="password" autoComplete="current-password" required className="min-h-11 w-full rounded-[10px] border border-tal-border bg-tal-surface px-3 text-sm outline-none focus:border-tal-ink focus:ring-2 focus:ring-tal-yellow" />
          </div>
          {error && <p role="alert" className="rounded-[10px] bg-tal-red-soft px-3 py-2 text-sm text-tal-red">{error}</p>}
          <button type="submit" disabled={busy} className="min-h-11 w-full rounded-[10px] bg-tal-yellow px-4 text-sm font-black text-tal-ink hover:bg-tal-yellow-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-tal-ink disabled:opacity-50">{busy ? "Signing in…" : "Sign in"}</button>
        </form>
      </section>
    </main>
  );
}
