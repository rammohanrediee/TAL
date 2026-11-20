"use client";

import { useAgent } from "agents/react";
import { useAgentChat } from "@cloudflare/ai-chat/react";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

type Conversation = { id: string; title: string; created_at: string };

async function conversations(path = "/", init?: RequestInit) {
  const response = await fetch(`/backend/api/v1/conversations${path}`, {
    credentials: "include",
    ...init,
  });
  if (response.status === 401) throw new Error("signed-out");
  if (!response.ok) throw new Error("Chat request failed");
  return response.status === 204 ? null : response.json();
}

function ConversationView({ id, host }: { id: string; host: string }) {
  const [input, setInput] = useState("");
  const agent = useAgent({
    agent: "TalChatAgent",
    name: id,
    host,
    query: async () => {
      const { token } = await conversations(`/${id}/connection-token`, { method: "POST" });
      return { token };
    },
    queryDeps: [id],
    cacheTtl: 0,
  });
  const { messages, sendMessage, status } = useAgentChat({ agent });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || status === "streaming" || status === "submitted") return;
    sendMessage({ text });
    setInput("");
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 space-y-5 overflow-y-auto px-5 py-8 sm:px-10">
        {messages.length === 0 && (
          <p className="mx-auto max-w-2xl text-sm text-neutral-500">
            Ask about your job search. Résumé and job analysis tools are coming next.
          </p>
        )}
        {messages.map((message) => (
          <div key={message.id} className={message.role === "user" ? "ml-auto max-w-2xl rounded-2xl bg-neutral-800 p-4" : "max-w-2xl p-4"}>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-yellow-400">{message.role === "user" ? "You" : "TAL"}</p>
            {message.parts.map((part, index) => part.type === "text" ? (
              <p key={index} className="whitespace-pre-wrap text-sm leading-7">{part.text}</p>
            ) : null)}
          </div>
        ))}
      </div>
      {status === "error" && <p role="alert" className="px-5 text-sm text-red-300">TAL could not reply. You can send another message.</p>}
      <form onSubmit={submit} className="flex gap-3 border-t border-white/10 p-4 sm:p-6">
        <label htmlFor="chat-message" className="sr-only">Message TAL</label>
        <input id="chat-message" value={input} onChange={(event) => setInput(event.target.value)}
          maxLength={4000} placeholder="Ask TAL about your job search"
          className="min-w-0 flex-1 rounded-xl border border-white/20 bg-neutral-900 px-4 py-3 text-sm outline-none focus:border-yellow-400" />
        <button type="submit" disabled={!input.trim() || status === "streaming" || status === "submitted"}
          className="rounded-xl bg-yellow-400 px-5 py-3 font-semibold text-black disabled:opacity-40">
          Send
        </button>
      </form>
    </div>
  );
}

export default function ChatWorkspace({ host }: { host: string }) {
  const router = useRouter();
  const [items, setItems] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    conversations().then(setItems).catch((failure) => {
      if (failure.message === "signed-out") router.replace("/login");
      else setError("Could not load your chats.");
    });
  }, [router]);

  async function create() {
    try {
      const item: Conversation = await conversations("/", { method: "POST" });
      setItems((current) => [item, ...current]);
      setSelected(item.id);
      setError("");
    } catch {
      setError("Could not create a chat.");
    }
  }

  async function remove(id: string) {
    try {
      await conversations(`/${id}`, { method: "DELETE" });
      setItems((current) => current.filter((item) => item.id !== id));
      if (selected === id) setSelected(null);
      setError("");
    } catch {
      setError("Could not delete the chat. Try again.");
    }
  }

  return (
    <div className="flex h-screen flex-col bg-neutral-950 text-white sm:flex-row">
      <aside className="flex max-h-48 w-full shrink-0 flex-col border-b border-white/10 p-4 sm:max-h-none sm:w-64 sm:border-b-0 sm:border-r">
        <Link href="/" className="mb-8 text-xl font-bold text-yellow-400">TAL</Link>
        <button onClick={create} className="rounded-xl bg-yellow-400 px-4 py-3 text-left font-semibold text-black">+ New chat</button>
        <div className="mt-5 flex-1 space-y-1 overflow-y-auto">
          {items.map((item) => (
            <div key={item.id} className="flex items-center gap-1">
              <button onClick={() => setSelected(item.id)} className={`min-w-0 flex-1 truncate rounded-lg px-3 py-2 text-left text-sm hover:bg-white/10 ${selected === item.id ? "bg-white/10" : ""}`}>
                {item.title} · {new Date(item.created_at).toLocaleDateString()}
              </button>
              <button onClick={() => remove(item.id)} aria-label="Delete chat" title="Delete chat" className="px-2 text-neutral-400 hover:text-white">×</button>
            </div>
          ))}
        </div>
        <Link href="/" className="text-sm text-neutral-400 hover:text-white">Résumé proofs</Link>
      </aside>
      <main className="flex min-h-0 min-w-0 flex-1 flex-col">
        {error && <p role="alert" className="bg-red-900/40 px-5 py-3 text-sm">{error}</p>}
        {selected ? <ConversationView key={selected} id={selected} host={host} /> : (
          <div className="flex flex-1 items-center justify-center p-6 text-center text-neutral-400">
            Start a chat or reopen one from the sidebar.
          </div>
        )}
      </main>
    </div>
  );
}
