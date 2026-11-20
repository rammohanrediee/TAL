"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";

export default function ChatLanding() {
  const router = useRouter();
  const picker = useRef<HTMLInputElement>(null);
  const [prompt, setPrompt] = useState(() =>
    typeof window === "undefined" ? "" : sessionStorage.getItem("tal:home-draft") ?? ""
  );
  const [file, setFile] = useState<File | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    sessionStorage.removeItem("tal:home-draft");
    fetch("/backend/api/v1/auth/me", { credentials: "include" })
      .then((response) => setSignedIn(response.ok))
      .catch(() => setSignedIn(false));
  }, []);

  function signIn() {
    sessionStorage.setItem("tal:home-draft", prompt);
    router.push("/login");
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if ((!prompt.trim() && !file) || busy) return;
    setBusy(true);
    setError("");
    try {
      const created = await fetch("/backend/api/v1/conversations", {
        method: "POST", credentials: "include",
      });
      if (created.status === 401) return signIn();
      if (!created.ok) throw new Error("Could not start a chat.");
      const { id } = await created.json() as { id: string };
      if (file) {
        const body = new FormData();
        body.append("file", file);
        const uploaded = await fetch(`/backend/api/v1/conversations/${id}/attachment`, {
          method: "POST", credentials: "include", body,
        });
        if (!uploaded.ok) {
          const data = await uploaded.json().catch(() => ({})) as { message?: string };
          throw new Error(data.message ?? "Could not attach that résumé.");
        }
      }
      sessionStorage.setItem(`tal:pending:${id}`, prompt.trim() || "What should I know about this résumé?");
      router.push(`/chat?conversation=${id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not start a chat.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-dvh flex-col bg-tal-canvas text-tal-ink">
      <header className="flex min-h-16 items-center justify-between border-b border-tal-border bg-white px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-3 text-xl font-bold"><span className="grid size-9 place-items-center rounded-xl bg-tal-yellow text-base">T</span>TAL</Link>
        <nav className="flex items-center gap-4 text-sm font-semibold">
          <Link href="/proofs" className="hover:underline">Résumé proofs</Link>
          <Link href={signedIn ? "/chat" : "/login"} className="rounded-xl bg-tal-ink px-4 py-3 text-white">{signedIn ? "Your chats" : "Sign in"}</Link>
        </nav>
      </header>
      <section className="mx-auto flex w-full max-w-4xl flex-1 flex-col justify-center px-4 py-12 sm:px-6">
        <p className="text-sm font-semibold text-tal-secondary">Your career, in conversation.</p>
        <h1 className="mt-4 max-w-2xl text-4xl font-black tracking-tight sm:text-6xl">What do you want to work on?</h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-tal-secondary sm:text-lg">Ask TAL about your job search. Attach a PDF or DOCX résumé when you want answers grounded in your experience.</p>
        <form onSubmit={send} className="mt-10 rounded-2xl bg-tal-ink p-3 text-white shadow-lg">
          <label htmlFor="home-prompt" className="sr-only">Message TAL</label>
          <textarea id="home-prompt" value={prompt} onChange={(event) => setPrompt(event.target.value)}
            maxLength={4000} rows={3} placeholder="Ask TAL about a role, your résumé, or your next move..."
            className="w-full resize-none rounded-xl bg-white/[.07] px-4 py-3 text-base outline-none placeholder:text-white/45 focus:ring-2 focus:ring-tal-yellow" />
          <input ref={picker} type="file" accept=".pdf,.docx" className="sr-only" aria-label="Attach a PDF or DOCX résumé"
            onChange={(event) => {
              const selected = event.target.files?.[0];
              if (selected && selected.size > 5 * 1024 * 1024) setError("Résumé must be 5 MB or smaller.");
              else { setFile(selected ?? null); setError(""); }
              event.target.value = "";
            }} />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 px-1">
            <div className="flex min-w-0 items-center gap-2">
              <button type="button" onClick={() => signedIn ? picker.current?.click() : signIn()} disabled={busy}
                className="min-h-11 rounded-xl border border-white/25 px-4 text-sm font-semibold hover:bg-white/10 disabled:opacity-50">＋ Attach résumé</button>
              {file && <button type="button" onClick={() => setFile(null)} className="max-w-48 truncate text-sm text-white/70 hover:text-white" title="Remove attachment">{file.name} ×</button>}
            </div>
            <button type="submit" disabled={busy || (!prompt.trim() && !file)}
              className="min-h-11 rounded-xl bg-tal-yellow px-6 font-bold text-tal-ink disabled:opacity-50">{busy ? "Starting…" : "Send →"}</button>
          </div>
        </form>
        {error && <p role="alert" className="mt-3 text-sm text-tal-red">{error}</p>}
        <p className="mt-4 text-sm text-tal-muted">Your file is stored privately. TAL sends up to 12,000 characters of its text to Cloudflare Workers AI for this chat.</p>
      </section>
    </main>
  );
}
