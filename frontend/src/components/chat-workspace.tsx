"use client";

import { useAgent } from "agents/react";
import { useAgentChat } from "@cloudflare/ai-chat/react";
import { Suspense, useEffect, useRef, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { MessageScroller, MessageScrollerButton, MessageScrollerContent, MessageScrollerItem, MessageScrollerProvider, MessageScrollerViewport } from "@/components/ui/message-scroller";
import { Message, MessageContent } from "@/components/ui/message";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import { ChatComposerAttachButton, ChatComposerAttachments, ChatComposerFooter, ChatComposerFrame, ChatComposerHeader, ChatComposerInput, ChatComposerSubmit, LocalChatComposerProvider } from "@/components/ui/chat-composer";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ChatSidebar as ChatcnSidebar, ChatSidebarAccount, type ChatThread } from "@/components/ui/chat-sidebar";
import { ArrowRight, LogOut, PanelLeft, X } from "lucide-react";
import { BriefcaseBusiness } from "lucide-react";
import JobsView from "./jobs-view";
import styles from "./chat-workspace.module.css";

type Conversation = { id: string; title: string; created_at: string };
type CurrentUser = { id: string; email: string; is_active: boolean };

function subscribeMobile(callback: () => void) {
  const media = window.matchMedia("(max-width: 767px)");
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}

function isMobileScreen() {
  return window.matchMedia("(max-width: 767px)").matches;
}

function ChatSidebar({ items, selected, section, onCreate, onSelect, onRemove, loading, error, onRetry, user, onLogout }: {
  items: Conversation[];
  selected: string | null;
  section: "chat" | "jobs";
  onCreate: () => Promise<void>;
  onSelect: (id: string) => void;
  onRemove: (id: string) => Promise<void>;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  user: CurrentUser;
  onLogout: () => Promise<void>;
}) {
  const mobile = useSyncExternalStore(subscribeMobile, isMobileScreen, () => false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [accountError, setAccountError] = useState("");
  const shellRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!accountOpen) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!shellRef.current?.contains(event.target as Node)) setAccountOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAccountOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [accountOpen]);
  const name = user.email.split("@")[0] || user.email;
  const threads: ChatThread[] = items.map((item) => ({
    id: item.id,
    title: item.title,
    updatedAt: item.created_at,
  }));

  return (
    <>
      {mobile && mobileOpen && <button type="button" className={styles.sidebarBackdrop} aria-label="Close sidebar" onClick={() => setMobileOpen(false)} />}
      <div ref={shellRef} className={`${styles.sidebarShell} ${mobileOpen ? styles.sidebarShellOpen : ""}`}>
        <ChatcnSidebar
          threads={threads}
          activeId={selected}
          onNewChat={() => { setMobileOpen(false); void onCreate(); }}
          onSelect={(id) => { onSelect(id); setMobileOpen(false); }}
          onDelete={(id) => { void onRemove(id); }}
          collapsed={mobile ? false : collapsed}
          onCollapsedChange={(next) => { if (mobile) setMobileOpen(!next); else setCollapsed(next); }}
          loading={loading}
          error={error}
          onRetry={onRetry}
          resizable={!mobile}
          brand={<Link href="/" className={styles.brand} title="TAL home"><span className={styles.brandTile}>T</span><span>TAL</span></Link>}
          header={<Link href="/jobs" aria-current={section === "jobs" ? "page" : undefined} className={styles.jobsNav}><BriefcaseBusiness aria-hidden="true" size={17} /> Jobs</Link>}
          railHeader={<Link href="/jobs" aria-current={section === "jobs" ? "page" : undefined} className={styles.jobsRail} aria-label="Jobs" title="Jobs"><BriefcaseBusiness aria-hidden="true" size={19} /></Link>}
          footer={<ChatSidebarAccount name={name} detail={user.email} aria-expanded={accountOpen} aria-haspopup="dialog" onClick={() => setAccountOpen((open) => !open)} />}
          railFooter={<ChatSidebarAccount name={name} detail={user.email} compact aria-expanded={accountOpen} aria-haspopup="dialog" onClick={() => setAccountOpen((open) => !open)} />}
          className={styles.chatcnSidebar}
        />
        {accountOpen && (
          <div className={styles.accountPopup} role="dialog" aria-label="Your account">
            <div className={styles.accountPopupHeader}>
              <span className={styles.accountAvatar} aria-hidden="true">{name.slice(0, 2).toUpperCase()}</span>
              <div className={styles.accountIdentity}><strong>{name}</strong><span title={user.email}>{user.email}</span></div>
              <button type="button" className={styles.accountClose} aria-label="Close account menu" onClick={() => setAccountOpen(false)}><X aria-hidden="true" size={18} /></button>
            </div>
            <div className={styles.accountPopupActions}>
              <button type="button" className={styles.accountLogout} onClick={() => { void onLogout().catch(() => setAccountError("Could not log out. Try again.")); }}><LogOut aria-hidden="true" size={18} />Log out</button>
              {accountError && <p role="alert" className={styles.accountError}>{accountError}</p>}
            </div>
          </div>
        )}
      </div>
      <button type="button" className={styles.mobileSidebarTrigger} aria-label="Open sidebar" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><PanelLeft aria-hidden="true" size={20} /></button>
    </>
  );
}

async function conversations(path = "", init?: RequestInit) {
  const response = await fetch(`/backend/api/v1/conversations${path}`, {
    credentials: "include",
    ...init,
  });
  if (response.status === 401) throw new Error("signed-out");
  if (!response.ok) throw new Error("Chat request failed");
  return response.status === 204 ? null : response.json();
}

function TalComposer({ id, onSend, disabled = false, attachedName }: {
  id: string;
  onSend: (text: string, file: File | null) => Promise<void>;
  disabled?: boolean;
  attachedName?: string;
}) {
  const [error, setError] = useState("");

  return (
    <div className={styles.composerDock}>
      {error && <p role="alert" className={styles.error}>{error}</p>}
      <div className={styles.composerForm}>
        <LocalChatComposerProvider
          disabled={disabled}
          onSubmit={async ({ value, attachments }) => {
            const file = attachments[0]?.file ?? null;
            if (attachments.length > 1) {
              setError("Attach one résumé at a time.");
              throw new Error("Too many attachments");
            }
            if (file && file.size > 5 * 1024 * 1024) {
              setError("Résumé must be 5 MB or smaller.");
              throw new Error("Attachment too large");
            }
            try {
              await onSend(value, file);
              setError("");
            } catch (caught) {
              setError(caught instanceof Error ? caught.message : "Could not send your message.");
              throw caught;
            }
          }}
        >
          <ChatComposerFrame className={styles.composer}>
            <ChatComposerHeader className={styles.composerHeader}>
              <label htmlFor={id} className={styles.composerLabel}>Your message</label>
            </ChatComposerHeader>
            <ChatComposerInput id={id} maxLength={4000} rows={3} placeholder="Ask TAL about a role, your résumé, or your next move…" className={styles.composerInput} />
            <ChatComposerAttachments className={styles.attachmentList} />
            {attachedName && <p className={styles.attachment}>Résumé attached · {attachedName}</p>}
            <ChatComposerFooter className={styles.composerActions}>
              <ChatComposerAttachButton accept=".pdf,.docx" label="Attach PDF or DOCX résumé" className={styles.attachButton} />
              <span className={styles.composerHint}>Enter to send · Shift+Enter for a new line</span>
              <ChatComposerSubmit className={styles.sendButton}>Send →</ChatComposerSubmit>
            </ChatComposerFooter>
          </ChatComposerFrame>
        </LocalChatComposerProvider>
      </div>
    </div>
  );
}

function ConnectedConversationView({ id, host, token }: { id: string; host: string; token: string }) {
  const [connected, setConnected] = useState(false);
  const [attachment, setAttachment] = useState("");
  const agent = useAgent({
    agent: "TalChatAgent",
    name: id,
    host,
    query: { token },
    onOpen: () => setConnected(true),
    onClose: () => setConnected(false),
  });
  const { messages, sendMessage, status } = useAgentChat({ agent });

  useEffect(() => {
    if (!connected || status !== "ready") return;
    const key = `tal:pending:${id}`;
    const pending = sessionStorage.getItem(key);
    if (!pending) return;
    sessionStorage.removeItem(key);
    sendMessage({ text: pending });
  }, [connected, id, sendMessage, status]);

  async function send(text: string, file: File | null) {
    if (!connected || status !== "ready") throw new Error("TAL is still connecting. Try again shortly.");
    if (file) {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch(`/backend/api/v1/conversations/${id}/attachment`, {
        method: "POST", credentials: "include", body,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({})) as { message?: string };
        throw new Error(data.message ?? "Could not attach that résumé.");
      }
      const { filename } = await response.json() as { filename: string };
      setAttachment(filename);
    }
    await Promise.resolve(sendMessage({ text: text || "What should I know about my attached résumé?" }));
  }

  return (
    <div className={styles.conversation}>
      <div className={styles.conversationHeader}>
        <div><p className={styles.eyebrow}>TAL / Conversation</p><h1>Ask with context.</h1></div>
        <span className={styles.connectionStatus} data-connected={connected}>{connected ? "Connected" : "Connecting"}</span>
      </div>
      <MessageScrollerProvider autoScroll>
      <MessageScroller className={styles.scroller}>
      <MessageScrollerViewport>
        <MessageScrollerContent className={styles.thread}>
        {messages.length === 0 && (
          <div className={styles.emptyState}>
            <p className={styles.eyebrow}>A place to start</p>
            <h2>What would you like to work through?</h2>
            <p>Ask about your job search. Attach a résumé when you want an answer grounded in your experience.</p>
          </div>
        )}
        {messages.map((message) => (
          <MessageScrollerItem key={message.id} messageId={message.id} scrollAnchor={message.role === "user"}>
            <Message align={message.role === "user" ? "end" : "start"}>
              <MessageContent>
                <Bubble align={message.role === "user" ? "end" : "start"} variant={message.role === "user" ? "muted" : "ghost"} className={message.role === "user" ? styles.userMessage : styles.assistantMessage}>
                  <BubbleContent className={styles.bubbleContent}>
                    <p className={styles.messageAuthor}>{message.role === "user" ? "You" : "TAL"}</p>
                    {message.parts.map((part, index) => part.type === "text" ? (
                      <p key={index} className={styles.messageText}>{part.text}</p>
                    ) : null)}
                  </BubbleContent>
                </Bubble>
              </MessageContent>
            </Message>
          </MessageScrollerItem>
        ))}
        {status === "submitted" && <p className={styles.replyStatus} role="status">TAL is preparing a reply…</p>}
        </MessageScrollerContent>
      </MessageScrollerViewport>
      <MessageScrollerButton />
      </MessageScroller>
      </MessageScrollerProvider>
      {status === "error" && <p role="alert" className={styles.error}>TAL could not reply. Try sending your message again.</p>}
      <TalComposer id="chat-message" onSend={send} disabled={!connected || status !== "ready"} attachedName={attachment} />
    </div>
  );
}

function ConversationView({ id, host }: { id: string; host: string }) {
  const [token, setToken] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    conversations(`/${id}/connection-token`, { method: "POST" })
      .then((result: { token: string }) => { if (active) { setToken(result.token); setFailed(false); } })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [id, attempt]);

  if (token) return (
    <Suspense fallback={<div className={styles.startView}><div className={styles.noConversation}><p className={styles.eyebrow}>Your conversation</p><h1>Loading your chat…</h1></div></div>}>
      <ConnectedConversationView id={id} host={host} token={token} />
    </Suspense>
  );

  const pending = typeof window === "undefined" ? "" : sessionStorage.getItem(`tal:pending:${id}`) ?? "";
  return (
    <div className={styles.startView}>
      <div className={styles.noConversation}>
        <p className={styles.eyebrow}>Your conversation</p>
        <h1>{failed ? "TAL could not connect." : "Connecting to TAL…"}</h1>
        <p>{failed ? "Your message is saved. Retry when the connection is available." : "Your message will send when the connection is ready."}</p>
      </div>
      {pending && <p className={styles.pendingMessage}>Saved message: {pending}</p>}
      {failed && <button type="button" className={styles.retryButton} onClick={() => { setFailed(false); setAttempt((value) => value + 1); }}>Retry connection</button>}
      <TalComposer id="pending-chat-message" disabled onSend={async () => {}} />
    </div>
  );
}

function StartConversationView({ onStart }: { onStart: (text: string, file: File | null) => Promise<boolean> }) {
  return (
    <div className={styles.startView}>
      <div className={styles.noConversation}>
        <p className={styles.eyebrow}>Your workspace</p>
        <h1>A conversation starts here.</h1>
        <p>Ask TAL about your job search, or attach a résumé for an answer grounded in your experience.</p>
      </div>
      <TalComposer id="new-chat-message" onSend={async (text, file) => {
        const started = await onStart(text, file);
        if (!started) throw new Error("Could not create a chat. Please try again.");
      }} />
    </div>
  );
}

export default function ChatWorkspace({ host, section = "chat" }: { host: string; section?: "chat" | "jobs" }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [authState, setAuthState] = useState<"checking" | "signed-out" | "unavailable" | "signed-in">("checking");
  const [authAttempt, setAuthAttempt] = useState(0);
  const [items, setItems] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [sidebarError, setSidebarError] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState("");
  const urlConversation = useSyncExternalStore(
    () => () => {},
    () => new URLSearchParams(window.location.search).get("conversation"),
    () => null,
  );
  const activeConversation = selected ?? urlConversation;

  useEffect(() => {
    const controller = new AbortController();
    fetch("/backend/api/v1/auth/me", { credentials: "include", signal: controller.signal })
      .then(async (response) => {
        if (response.status === 401) { setAuthState("signed-out"); return; }
        if (!response.ok) throw new Error("Could not check sign-in status");
        setUser(await response.json() as CurrentUser);
        setAuthState("signed-in");
      })
      .catch(() => { if (!controller.signal.aborted) setAuthState("unavailable"); });
    return () => controller.abort();
  }, [authAttempt]);

  async function loadConversations() {
    setLoading(true);
    setSidebarError(false);
    try {
      const loaded = await conversations() as Conversation[];
      setItems(loaded);
    } catch (failure) {
      if (failure instanceof Error && failure.message === "signed-out") { setUser(null); setAuthState("signed-out"); }
      else setSidebarError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!user) return;
    queueMicrotask(() => { void loadConversations(); });
  }, [user]);

  async function start(text = "", file: File | null = null): Promise<boolean> {
    try {
      const item: Conversation = await conversations("", { method: "POST" });
      if (file) {
        const body = new FormData();
        body.append("file", file);
        const uploaded = await fetch(`/backend/api/v1/conversations/${item.id}/attachment`, { method: "POST", credentials: "include", body });
        if (!uploaded.ok) throw new Error("Could not attach that résumé.");
      }
      if (text || file) sessionStorage.setItem(`tal:pending:${item.id}`, text || "What should I know about my attached résumé?");
      setItems((current) => [item, ...current]);
      setSelected(item.id);
      if (section === "jobs") window.location.assign(`/chat?conversation=${item.id}`);
      setError("");
      return true;
    } catch (failure) {
      if (failure instanceof Error && failure.message === "signed-out") { setUser(null); setAuthState("signed-out"); return false; }
      if (!text && !file) setError("Could not create a chat. Please try again.");
      return false;
    }
  }

  async function create() { await start(); }

  async function remove(id: string) {
    try {
      await conversations(`/${id}`, { method: "DELETE" });
      setItems((current) => current.filter((item) => item.id !== id));
      if (activeConversation === id) setSelected("");
      setError("");
    } catch {
      setError("Could not delete the chat. Try again.");
    }
  }

  async function logout() {
    const response = await fetch("/backend/api/v1/auth/logout", { method: "POST", credentials: "include" });
    if (!response.ok) throw new Error("Could not log out");
    setUser(null);
    setAuthState("signed-out");
    setItems([]);
    setSelected(null);
  }

  if (authState !== "signed-in" || !user) {
    return (
      <main className={styles.authGate}>
        <Link href="/" className={styles.authBrand}><span className={styles.brandTile}>T</span>TAL</Link>
        <div className={styles.authDialog} role="dialog" aria-label="Sign in to TAL">
          <p className={styles.eyebrow}>TAL / {section === "jobs" ? "Jobs" : "Chat"}</p>
          <h1>{authState === "checking" ? "Checking your account…" : authState === "unavailable" ? "We couldn’t reach TAL." : "Please sign in."}</h1>
          <p>{authState === "checking" ? "Your workspace will appear in a moment." : authState === "unavailable" ? "Check your connection and try again." : section === "jobs" ? "Sign in to watch company boards and see open jobs." : "Sign in to see your conversations and start a new chat."}</p>
          {authState === "signed-out" && <Link href="/login" className={styles.signInButton}>Sign in <ArrowRight aria-hidden="true" size={18} /></Link>}
          {authState === "unavailable" && <button type="button" className={styles.signInButton} onClick={() => { setAuthState("checking"); setAuthAttempt((attempt) => attempt + 1); }}>Retry <ArrowRight aria-hidden="true" size={18} /></button>}
        </div>
      </main>
    );
  }

  return (
    <TooltipProvider>
    <div className={styles.workspace}>
      <ChatSidebar items={items} selected={activeConversation} section={section} onCreate={create} onSelect={(id) => { if (section === "jobs") window.location.assign(`/chat?conversation=${id}`); else setSelected(id); }} onRemove={remove} loading={loading} error={sidebarError} onRetry={() => { void loadConversations(); }} user={user} onLogout={logout} />
      <main className={styles.main}>
        <div className={styles.topBar}>
          <span>Workspace / {section === "jobs" ? "Jobs" : "Chat"}</span>
          {section === "jobs" && <Link href="/chat" className={styles.topBarLink}>Chat</Link>}
        </div>
        {error && <p role="alert" className={styles.error}>{error}</p>}
        {section === "jobs" ? <JobsView /> : activeConversation ? <ConversationView key={activeConversation} id={activeConversation} host={host} /> : <StartConversationView onStart={start} />}
      </main>
    </div>
    </TooltipProvider>
  );
}
