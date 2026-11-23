"use client";

import { useAgent } from "agents/react";
import { useAgentChat } from "@cloudflare/ai-chat/react";
import { Suspense, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { MessageScroller, MessageScrollerButton, MessageScrollerContent, MessageScrollerItem, MessageScrollerProvider, MessageScrollerViewport } from "@/components/ui/message-scroller";
import { Message, MessageContent } from "@/components/ui/message";
import { Bubble, BubbleContent } from "@/components/ui/bubble";
import { TalChatComposer } from "@/components/tal-chat-composer";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ChatSidebar as ChatcnSidebar, ChatSidebarAccount, type ChatThread } from "@/components/ui/chat-sidebar";
import { ArrowRight, LogOut, PanelLeft, X } from "lucide-react";
import { BriefcaseBusiness, ClipboardList } from "lucide-react";
import JobsView from "./jobs-view";
import ApplicationsView from "./applications-view";
import JobSearchCards, { extractJobSearchFromMessageParts } from "@/components/job-search-cards";
import { apiFetch, apiFetchWithTimeout, BOOTSTRAP_REQUEST_TIMEOUT_MS, delay, isTransientHttpStatus } from "@/lib/api";
import styles from "./chat-workspace.module.css";

type Conversation = { id: string; title: string; created_at: string };
type CurrentUser = { id: string; email: string; is_active: boolean; name?: string | null; full_name?: string | null };

function getTimeGreeting(now = new Date()): string {
  const hour = now.getHours();
  if (hour >= 5 && hour <= 11) return "Good morning";
  if (hour >= 12 && hour <= 16) return "Good afternoon";
  if (hour >= 17 && hour <= 21) return "Good evening";
  return "Good night";
}

function titleCaseLocalPart(segment: string): string {
  const letters = segment.replace(/\d+$/, "");
  const source = letters.length > 0 ? letters : segment;
  return source.charAt(0).toUpperCase() + source.slice(1).toLowerCase();
}

function getDisplayName(user: CurrentUser): string {
  const fromApi = user.name?.trim() || user.full_name?.trim();
  if (fromApi) {
    const first = fromApi.split(/\s+/)[0] ?? fromApi;
    return first.charAt(0).toUpperCase() + first.slice(1);
  }
  const local = user.email.split("@")[0] ?? "";
  const segment = local.includes(".") ? (local.split(".")[0] ?? local) : local;
  return titleCaseLocalPart(segment);
}

const JOB_SEARCH_STARTERS = [
  "Find remote Python backend roles posted in the last 30 days",
  "Search senior software engineer jobs and rank them by résumé fit",
  "Show me product manager openings with strong skill match",
] as const;

function textFromMessagePart(part: unknown): string | null {
  if (!part || typeof part !== "object") return null;
  const record = part as Record<string, unknown>;
  const type = String(record.type ?? "");
  if (type === "reasoning") return null;
  if (typeof record.text === "string" && (type === "text" || type.startsWith("text"))) {
    return record.text;
  }
  return null;
}

function textFromMessage(message: { parts?: unknown[]; content?: unknown }): string {
  if (Array.isArray(message.parts)) {
    const chunks = message.parts.map(textFromMessagePart).filter((chunk): chunk is string => Boolean(chunk));
    if (chunks.length > 0) return chunks.join("");
  }
  if (typeof message.content === "string") return message.content;
  return "";
}

function subscribeChatHost(callback: () => void) {
  const onChange = () => callback();
  window.addEventListener("pageshow", onChange);
  return () => window.removeEventListener("pageshow", onChange);
}

function chatAgentHost(fallbackHost: string): string {
  const explicit = process.env.NEXT_PUBLIC_TAL_CHAT_URL?.trim();
  if (explicit) {
    const source = explicit.includes("://") ? explicit : `https://${explicit}`;
    return new URL(source).host;
  }
  // Vercel cannot reliably proxy WebSockets; connect to the Worker host from build-time env.
  if (fallbackHost && !/^(127\.0\.0\.1|localhost)(:\d+)?$/i.test(fallbackHost)) {
    return fallbackHost;
  }
  if (typeof window !== "undefined") return window.location.host;
  return fallbackHost;
}

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
  section: "chat" | "jobs" | "applications";
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
          header={<><Link href="/jobs" aria-current={section === "jobs" ? "page" : undefined} className={styles.jobsNav}><BriefcaseBusiness aria-hidden="true" size={17} /> Jobs</Link><Link href="/applications" aria-current={section === "applications" ? "page" : undefined} className={styles.jobsNav}><ClipboardList aria-hidden="true" size={17} /> Applications</Link></>}
          railHeader={<><Link href="/jobs" aria-current={section === "jobs" ? "page" : undefined} className={styles.jobsRail} aria-label="Jobs" title="Jobs"><BriefcaseBusiness aria-hidden="true" size={19} /></Link><Link href="/applications" aria-current={section === "applications" ? "page" : undefined} className={styles.jobsRail} aria-label="Applications" title="Applications"><ClipboardList aria-hidden="true" size={19} /></Link></>}
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

const BOOTSTRAP_MAX_ATTEMPTS = 4;

async function conversations(path = "", init?: RequestInit) {
  const response = await apiFetchWithTimeout(`/backend/api/v1/conversations${path}`, init);
  if (response.status === 401) throw new Error("signed-out");
  if (!response.ok) {
    const data = await response.json().catch(() => ({})) as { code?: string; detail?: string };
    if (response.status === 403 && data.code === "csrf_failed") throw new Error("csrf");
    if (response.status === 503) throw new Error("unavailable");
    throw new Error(data.detail ? String(data.detail) : `Chat request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

function TalComposer(props: {
  id: string;
  onSend: (text: string, file: File | null) => Promise<void>;
  disabled?: boolean;
  connecting?: boolean;
  attachedName?: string;
}) {
  return <TalChatComposer {...props} />;
}

function ConnectedConversationView({
  id,
  fallbackHost,
  token,
  onConnectionLost,
}: {
  id: string;
  fallbackHost: string;
  token: string;
  onConnectionLost?: () => void;
}) {
  const [connected, setConnected] = useState(false);
  const [attachment, setAttachment] = useState("");
  const agentHost = useSyncExternalStore(subscribeChatHost, () => chatAgentHost(fallbackHost), () => fallbackHost);
  const chatAuthHeaders = useMemo(
    () => ({ Authorization: `Bearer ${token}` }),
    [token],
  );
  const agent = useAgent({
    agent: "TalChatAgent",
    name: id,
    host: agentHost,
    protocols: [token],
    onOpen: () => setConnected(true),
    onClose: () => setConnected(false),
    onConnectionError: () => onConnectionLost?.(),
  });
  const { messages, sendMessage, status, error: chatError } = useAgentChat({ agent, headers: chatAuthHeaders });

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
      const response = await apiFetch(`/backend/api/v1/conversations/${id}/attachment`, {
        method: "POST", body,
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
            <p className={styles.trustLine}>Fit scores reflect résumé evidence, not hiring odds.</p>
            <ul className={styles.suggestedPrompts} aria-label="Suggested job-search prompts">
              {JOB_SEARCH_STARTERS.map((text) => (
                <li key={text}>
                  <button
                    type="button"
                    className={styles.suggestedPrompt}
                    disabled={!connected || status !== "ready"}
                    onClick={() => void sendMessage({ text })}
                  >
                    {text}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {messages.map((message, index) => {
          const jobResults = message.role === "assistant"
            ? extractJobSearchFromMessageParts(message.parts)
            : null;
          const bodyText = textFromMessage(message);
          const anchorToEnd = index === messages.length - 1;
          const scrollAnchor = anchorToEnd || Boolean(jobResults);
          return (
          <MessageScrollerItem
            key={message.id}
            messageId={message.id}
            scrollAnchor={scrollAnchor}
            className={styles.messageScrollItem}
          >
            <Message align={message.role === "user" ? "end" : "start"}>
              <MessageContent>
                <Bubble align={message.role === "user" ? "end" : "start"} variant={message.role === "user" ? "muted" : "ghost"} className={message.role === "user" ? styles.userMessage : styles.assistantMessage}>
                  <BubbleContent className={styles.bubbleContent}>
                    <p className={styles.messageAuthor}>{message.role === "user" ? "You" : "TAL"}</p>
                    {bodyText ? (
                      <p className={styles.messageText}>{bodyText}</p>
                    ) : message.parts.map((part, partIndex) => {
                      const chunk = textFromMessagePart(part);
                      return chunk ? (
                        <p key={partIndex} className={styles.messageText}>{chunk}</p>
                      ) : null;
                    })}
                    {jobResults && <JobSearchCards jobs={jobResults} />}
                  </BubbleContent>
                </Bubble>
              </MessageContent>
            </Message>
          </MessageScrollerItem>
          );
        })}
        {(status === "submitted" || status === "streaming") && (
          <p className={styles.replyStatus} role="status">
            {status === "streaming" ? "TAL is typing…" : "TAL is preparing a reply…"}
          </p>
        )}
        </MessageScrollerContent>
      </MessageScrollerViewport>
      <MessageScrollerButton />
      </MessageScroller>
      </MessageScrollerProvider>
      {(status === "error" || chatError) && (
        <p role="alert" className={styles.error}>
          TAL could not reply. {chatError instanceof Error ? chatError.message : "Try sending your message again."}
        </p>
      )}
      <TalComposer
        id="chat-message"
        onSend={send}
        disabled={!connected || status !== "ready"}
        connecting={!connected || status !== "ready"}
        attachedName={attachment}
      />
    </div>
  );
}

function ConversationView({
  id,
  host,
  onSessionLost,
}: {
  id: string;
  host: string;
  onSessionLost?: () => void;
}) {
  const [token, setToken] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [failureDetail, setFailureDetail] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setFailureDetail("");
    conversations(`/${id}/connection-token`, { method: "POST" })
      .then((result: { token: string }) => {
        if (active) {
          setToken(result.token);
          setFailed(false);
          setFailureDetail("");
        }
      })
      .catch((failure: unknown) => {
        if (!active) return;
        if (failure instanceof Error) {
          if (failure.message === "signed-out") {
            onSessionLost?.();
            return;
          }
          if (failure.message === "csrf") {
            setFailureDetail("Your session needs a refresh. Sign out and back in, then retry.");
          } else if (failure.message === "unavailable") {
            setFailureDetail("TAL is still starting up. Wait a moment and retry.");
          } else {
            setFailureDetail(failure.message);
          }
        }
        setFailed(true);
      });
    return () => { active = false; };
  }, [id, attempt, onSessionLost]);

  if (token) return (
    <Suspense fallback={<div className={styles.startView}><div className={styles.noConversation}><p className={styles.eyebrow}>Your conversation</p><h1>Loading your chat…</h1></div></div>}>
      <ConnectedConversationView
        id={id}
        fallbackHost={host}
        token={token}
        onConnectionLost={() => {
          setToken(null);
          setFailed(true);
          setFailureDetail("The live chat link dropped. Retry to request a new connection token.");
        }}
      />
    </Suspense>
  );

  const pending = typeof window === "undefined" ? "" : sessionStorage.getItem(`tal:pending:${id}`) ?? "";
  return (
    <div className={styles.startView}>
      <div className={styles.noConversation}>
        <p className={styles.eyebrow}>Your conversation</p>
        <h1>{failed ? "TAL could not connect." : "Connecting to TAL…"}</h1>
        <p>{failed
          ? (failureDetail || "Your message is saved. Retry when the connection is available.")
          : "Your message will send when the connection is ready."}</p>
      </div>
      {pending && <p className={styles.pendingMessage}>Saved message: {pending}</p>}
      {failed && (
        <button
          type="button"
          className={styles.retryButton}
          onClick={() => {
            setFailed(false);
            setFailureDetail("");
            setAttempt((value) => value + 1);
          }}
        >
          Retry connection
        </button>
      )}
      <TalComposer id="pending-chat-message" disabled onSend={async () => {}} />
    </div>
  );
}

function StartConversationView({ user, onStart }: { user: CurrentUser; onStart: (text: string, file: File | null) => Promise<boolean> }) {
  const displayName = getDisplayName(user);
  const heroTitle = `${getTimeGreeting()}, ${displayName}. How can I help you?`;

  return (
    <div className={styles.startView}>
      <div className={styles.noConversation}>
        <h1>{heroTitle}</h1>
        <p>Ask TAL about your job search, or attach a résumé for an answer grounded in your experience.</p>
        <p className={styles.trustLine}>Fit scores reflect résumé evidence, not hiring odds.</p>
      </div>
      <ul className={styles.suggestedPrompts} aria-label="Suggested job-search prompts">
        {JOB_SEARCH_STARTERS.map((text) => (
          <li key={text}>
            <button type="button" className={styles.suggestedPrompt} onClick={() => void onStart(text, null)}>
              {text}
            </button>
          </li>
        ))}
      </ul>
      <TalComposer id="new-chat-message" onSend={async (text, file) => {
        const started = await onStart(text, file);
        if (!started) throw new Error("Could not create a chat. Please try again.");
      }} />
    </div>
  );
}

export default function ChatWorkspace({ host, section = "chat" }: { host: string; section?: "chat" | "jobs" | "applications" }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [authState, setAuthState] = useState<"checking" | "signed-out" | "unavailable" | "signed-in">("checking");
  const [authHint, setAuthHint] = useState("");
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

    async function bootstrap() {
      setAuthHint("");
      setLoading(true);
      setSidebarError(false);
      let signedOut = false;
      let startupLikely = false;

      const finishUnavailable = () => {
        setAuthHint(
          startupLikely
            ? "The API can be slow to wake after idle time. Check your connection or retry."
            : "Check your connection and try again.",
        );
        setUser(null);
        setAuthState("unavailable");
        setLoading(false);
      };

      for (let attempt = 0; attempt < BOOTSTRAP_MAX_ATTEMPTS; attempt++) {
        if (controller.signal.aborted) return;
        if (attempt > 0) {
          setAuthHint("TAL is still starting up. This can take a moment after idle time.");
          await delay(600 * attempt, controller.signal);
        }

        try {
          const [meResponse, conversationsResponse] = await Promise.all([
            apiFetchWithTimeout("/backend/api/v1/auth/me", {
              signal: controller.signal,
              timeoutMs: BOOTSTRAP_REQUEST_TIMEOUT_MS,
            }),
            apiFetchWithTimeout("/backend/api/v1/conversations", {
              signal: controller.signal,
              timeoutMs: BOOTSTRAP_REQUEST_TIMEOUT_MS,
            }),
          ]);

          if (meResponse.status === 401 || conversationsResponse.status === 401) {
            signedOut = true;
            break;
          }

          if (!meResponse.ok) {
            startupLikely ||= isTransientHttpStatus(meResponse.status);
            if (isTransientHttpStatus(meResponse.status) && attempt < BOOTSTRAP_MAX_ATTEMPTS - 1) {
              continue;
            }
            throw new Error(`auth/me ${meResponse.status}`);
          }

          const nextUser = await meResponse.json() as CurrentUser;
          setUser(nextUser);
          setAuthState("signed-in");
          setAuthHint("");

          if (conversationsResponse.ok) {
            setItems(await conversationsResponse.json() as Conversation[]);
            setLoading(false);
            return;
          }

          if (isTransientHttpStatus(conversationsResponse.status)) {
            startupLikely = true;
            if (attempt < BOOTSTRAP_MAX_ATTEMPTS - 1) continue;
          }

          setSidebarError(true);
          setLoading(false);
          return;
        } catch (failure) {
          if (controller.signal.aborted) return;
          if (failure instanceof DOMException && failure.name === "AbortError") return;
          startupLikely = true;
          if (attempt < BOOTSTRAP_MAX_ATTEMPTS - 1) continue;
          finishUnavailable();
          return;
        }
      }

      if (controller.signal.aborted) return;
      if (signedOut) {
        setUser(null);
        setAuthState("signed-out");
        setLoading(false);
        return;
      }
      finishUnavailable();
    }

    void bootstrap();
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

  async function start(text = "", file: File | null = null): Promise<boolean> {
    try {
      const item: Conversation = await conversations("", { method: "POST" });
      if (file) {
        const body = new FormData();
        body.append("file", file);
        const uploaded = await apiFetch(`/backend/api/v1/conversations/${item.id}/attachment`, { method: "POST", body });
        if (!uploaded.ok) throw new Error("Could not attach that résumé.");
      }
      if (text || file) sessionStorage.setItem(`tal:pending:${item.id}`, text || "What should I know about my attached résumé?");
      setItems((current) => [item, ...current]);
      setSelected(item.id);
      if (section !== "chat") window.location.assign(`/chat?conversation=${item.id}`);
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
    const response = await apiFetch("/backend/api/v1/auth/logout", { method: "POST" });
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
          <p className={styles.eyebrow}>TAL / {section === "jobs" ? "Jobs" : section === "applications" ? "Applications" : "Chat"}</p>
          <h1>{authState === "checking" ? "Checking your account…" : authState === "unavailable" ? "We couldn’t reach TAL." : "Please sign in."}</h1>
          <p>{authState === "checking"
            ? (authHint || "Your workspace will appear in a moment.")
            : authState === "unavailable"
              ? (authHint || "Check your connection and try again.")
              : section === "jobs"
                ? "Sign in to watch company boards and see open jobs."
                : section === "applications"
                  ? "Sign in to manage your applications."
                  : "Sign in to see your conversations and start a new chat."}</p>
          {authState === "signed-out" && <Link href="/login" className={styles.signInButton}>Sign in <ArrowRight aria-hidden="true" size={18} /></Link>}
          {authState === "unavailable" && <button type="button" className={styles.signInButton} onClick={() => { setAuthHint(""); setAuthState("checking"); setAuthAttempt((attempt) => attempt + 1); }}>Retry <ArrowRight aria-hidden="true" size={18} /></button>}
        </div>
      </main>
    );
  }

  return (
    <TooltipProvider>
    <div className={styles.workspace}>
      <ChatSidebar items={items} selected={activeConversation} section={section} onCreate={create} onSelect={(id) => { if (section !== "chat") window.location.assign(`/chat?conversation=${id}`); else setSelected(id); }} onRemove={remove} loading={loading} error={sidebarError} onRetry={() => { void loadConversations(); }} user={user} onLogout={logout} />
      <main className={styles.main}>
        <div className={styles.topBar}>
          <span>{section === "jobs" ? "Jobs" : section === "applications" ? "Applications" : "Chat"}</span>
          {section !== "chat" && <Link href="/chat" className={styles.topBarLink}>Chat</Link>}
        </div>
        {error && <p role="alert" className={styles.error}>{error}</p>}
        {section === "jobs" ? <JobsView /> : section === "applications" ? <ApplicationsView /> : activeConversation ? (
          <ConversationView
            key={activeConversation}
            id={activeConversation}
            host={host}
            onSessionLost={() => {
              setUser(null);
              setAuthState("signed-out");
            }}
          />
        ) : (
          <StartConversationView user={user} onStart={start} />
        )}
      </main>
    </div>
    </TooltipProvider>
  );
}
