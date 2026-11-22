"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type Application = { id: string; company_name: string; role_title: string; status: string; job_url: string | null };

export default function ApplicationsView() {
  const [items, setItems] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    apiFetch("/backend/api/v1/applications/", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load applications.");
        setItems(await response.json() as Application[]);
      })
      .catch(() => { if (!controller.signal.aborted) setError("Could not load applications. Refresh to try again."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  async function remove(item: Application) {
    if (!window.confirm(`Delete your application for ${item.role_title} at ${item.company_name}?`)) return;
    setDeletingId(item.id);
    setError("");
    try {
      const response = await apiFetch(`/backend/api/v1/applications/${item.id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Could not delete the application. Try again.");
      setItems((current) => current.filter((entry) => entry.id !== item.id));
    } catch {
      setError("Could not delete the application. Try again.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 text-tal-ink sm:px-8 sm:py-12">
      <p className="text-sm font-semibold text-tal-secondary">TAL / Applications</p>
      <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-5xl">Your applications</h1>
      <p className="mt-3 text-sm text-tal-secondary">Keep track of the roles you have saved and applied to.</p>
      {error && <p role="alert" className="mt-6 rounded-[10px] bg-tal-red-soft px-4 py-3 text-sm text-tal-red">{error}</p>}
      {loading ? <p role="status" className="mt-8 text-tal-secondary">Loading applications…</p> : items.length === 0 ? <p className="mt-8 rounded-[14px] border border-tal-border bg-white p-6 text-tal-secondary">No applications yet.</p> : (
        <ul className="mt-8 divide-y divide-tal-border rounded-[14px] border border-tal-border bg-white px-5">
          {items.map((item) => <li key={item.id} className="flex flex-wrap items-center justify-between gap-4 py-5">
            <div className="min-w-0">
              <h2 className="font-bold">{item.role_title}</h2>
              <p className="mt-1 text-sm text-tal-secondary">{item.company_name} · {item.status}</p>
              {item.job_url && <a href={item.job_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm font-semibold underline underline-offset-2">View job</a>}
            </div>
            <button type="button" onClick={() => void remove(item)} disabled={deletingId !== null} className="min-h-11 rounded-[10px] border border-tal-border px-4 text-sm font-semibold text-tal-red hover:bg-tal-red-soft disabled:cursor-wait disabled:opacity-50" aria-label={`Delete application for ${item.role_title} at ${item.company_name}`}>
              {deletingId === item.id ? "Deleting…" : "Delete"}
            </button>
          </li>)}
        </ul>
      )}
    </div>
  );
}
