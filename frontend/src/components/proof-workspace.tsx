"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";

type ResumeStatus = "uploaded" | "processing" | "ready" | "failed";
type EvidenceStatus = "pending" | "confirmed" | "corrected" | "rejected";
type LoadState = "idle" | "loading" | "ready" | "error";

interface ResumeRead {
  id: string;
  original_filename: string;
  status: ResumeStatus;
}

interface EvidenceRead {
  id: string;
  evidence_type: "experience" | "project" | "skill" | "education" | "achievement";
  status: EvidenceStatus;
  extracted_text: string;
  corrected_text: string | null;
  source_text: string;
  canonical_skill_name: string | null;
}

interface CurrentUser {
  id: string;
  email: string;
}

interface ApiError {
  message?: string;
  detail?: string;
}

const POLL_INTERVAL_MS = 1_000;
const MAX_POLL_ATTEMPTS = 30;

function SvgIcon({ children, className = "size-5" }: { children: ReactNode; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className} aria-hidden="true">
      {children}
    </svg>
  );
}

function PlusIcon() {
  return <SvgIcon><path d="M12 5v14M5 12h14" strokeLinecap="round" /></SvgIcon>;
}

function HomeIcon() {
  return <SvgIcon><path d="m3.5 10.5 8.5-7 8.5 7M5.5 9.5V21h13V9.5M9.5 21v-6h5v6" strokeLinecap="round" strokeLinejoin="round" /></SvgIcon>;
}

function DocumentIcon({ className }: { className?: string }) {
  return <SvgIcon className={className}><path d="M7 3h7l4 4v14H7zM14 3v5h5M9.5 12h5M9.5 16h5" strokeLinecap="round" strokeLinejoin="round" /></SvgIcon>;
}

function BriefcaseIcon() {
  return <SvgIcon><path d="M4 8h16v11H4zM9 8V5h6v3M4 12h16" strokeLinecap="round" strokeLinejoin="round" /></SvgIcon>;
}

function PaperclipIcon() {
  return <SvgIcon><path d="m9.5 12.5 5.4-5.4a3 3 0 0 1 4.2 4.2l-7.5 7.5a5 5 0 0 1-7.1-7.1l7.2-7.2" strokeLinecap="round" strokeLinejoin="round" /></SvgIcon>;
}

function CheckIcon({ className = "size-5" }: { className?: string }) {
  return <SvgIcon className={className}><path d="m5 12 4.5 4.5L19 7" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></SvgIcon>;
}

function PencilIcon() {
  return <SvgIcon className="size-4"><path d="m4 20 4.1-1 10.7-10.7a2 2 0 0 0-2.8-2.8L5.3 16.2 4 20Z" strokeLinecap="round" strokeLinejoin="round" /></SvgIcon>;
}

function ChevronIcon({ open }: { open: boolean }) {
  return <SvgIcon className={`size-5 transition-transform duration-200 motion-reduce:transition-none ${open ? "rotate-180" : ""}`}><path d="m7 9.5 5 5 5-5" strokeLinecap="round" strokeLinejoin="round" /></SvgIcon>;
}

function apiMessage(error: ApiError, fallback: string) {
  return error.detail ?? error.message ?? fallback;
}

function evidenceTypeLabel(type: EvidenceRead["evidence_type"]) {
  return { experience: "Experience", project: "Project", skill: "Skill", education: "Education", achievement: "Achievement" }[type];
}

function evidenceStatusLabel(status: EvidenceStatus) {
  return { pending: "Needs review", confirmed: "Verified", corrected: "Corrected", rejected: "Not supported" }[status];
}

function ResumeFile({ resume }: { resume: ResumeRead }) {
  return (
    <div className="flex min-w-0 items-center gap-3 rounded-[14px] bg-tal-ink px-4 py-3 text-white">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-[10px] bg-white/10 text-tal-yellow"><DocumentIcon /></span>
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold" title={resume.original_filename}>{resume.original_filename}</span>
        <span className="mt-0.5 block text-xs text-white/55">Private PDF or DOCX</span>
      </span>
    </div>
  );
}

function AnalysisStep({ state, label, detail, last = false }: { state: "done" | "current" | "waiting" | "error"; label: string; detail: string; last?: boolean }) {
  const dotClass = state === "done" ? "border-tal-green bg-tal-green text-white" : state === "current" ? "border-tal-yellow bg-tal-ink text-tal-yellow" : state === "error" ? "border-tal-red bg-tal-red text-white" : "border-white/20 bg-tal-ink text-white/30";
  return (
    <li className="grid grid-cols-[2rem_minmax(0,1fr)] gap-3">
      <span className="relative flex justify-center">
        {!last && <span aria-hidden="true" className={`absolute bottom-0 top-7 w-px ${state === "done" ? "bg-tal-green" : "bg-white/15"}`} />}
        <span className={`relative z-10 flex size-7 items-center justify-center rounded-full border-2 ${dotClass}`}>
          {state === "done" ? <CheckIcon className="size-4" /> : state === "error" ? "!" : state === "current" ? <span className="size-2 rounded-full bg-tal-yellow" /> : null}
        </span>
      </span>
      <span className={last ? "" : "pb-5"}>
        <span className={`block text-sm font-semibold ${state === "current" ? "text-tal-yellow" : state === "waiting" ? "text-white/40" : "text-white"}`}>{label}</span>
        <span className="mt-1 block text-xs leading-5 text-white/50">{detail}</span>
      </span>
    </li>
  );
}

function AnalysisPanel({ resume, open, onToggle }: { resume: ResumeRead; open: boolean; onToggle: () => void }) {
  const ready = resume.status === "ready";
  const failed = resume.status === "failed";
  return (
    <section className="overflow-hidden rounded-[16px] bg-tal-ink text-white" aria-labelledby="analysis-heading">
      <button type="button" onClick={onToggle} aria-expanded={open} aria-controls="analysis-progress" className="flex min-h-16 w-full items-center gap-3 px-5 py-4 text-left transition-colors hover:bg-white/[0.04]">
        <span className={`flex size-9 shrink-0 items-center justify-center rounded-full ${ready ? "bg-tal-green" : failed ? "bg-tal-red" : "tal-working-ring"}`}>
          {ready ? <CheckIcon /> : failed ? "!" : null}
        </span>
        <span className="min-w-0 flex-1">
          <span id="analysis-heading" className="block text-base font-semibold">{ready ? "Analyzed résumé" : failed ? "Analysis stopped" : "Analyzing"}</span>
          <span className="mt-0.5 block truncate text-sm text-white/55" title={resume.original_filename}>{ready ? "Proofs ready with exact sources" : failed ? "This résumé could not be processed" : resume.original_filename}</span>
        </span>
        <ChevronIcon open={open} />
      </button>
      {open && (
        <div id="analysis-progress" className="border-t border-white/10 px-5 pb-5 pt-4">
          <ol aria-label="Résumé processing progress">
            <AnalysisStep state="done" label="Résumé received" detail={resume.original_filename} />
            <AnalysisStep state={ready ? "done" : failed ? "error" : "current"} label="Finding proof" detail={failed ? "Processing failed" : "Skills, experience, projects, education, and achievements"} />
            <AnalysisStep state={ready ? "done" : "waiting"} label="Linking exact sources" detail={ready ? "Every claim is connected to its source quote" : "TAL only presents claims it can cite"} last />
          </ol>
          <p className="mt-4 border-t border-white/10 pt-4 text-xs leading-5 text-white/50">These are progress summaries, not private model reasoning. Collapse this panel whenever you want.</p>
        </div>
      )}
    </section>
  );
}

function EvidenceSkeleton() {
  return (
    <div className="divide-y divide-tal-border border-y border-tal-border" aria-label="Loading résumé evidence">
      {[0, 1, 2].map((item) => (
        <div key={item} className="grid gap-4 py-6 md:grid-cols-[2rem_minmax(0,.9fr)_minmax(0,1.1fr)]">
          <div className="tal-skeleton size-8 rounded-full" />
          <div className="space-y-3"><div className="tal-skeleton h-4 w-24 rounded" /><div className="tal-skeleton h-5 w-4/5 rounded" /></div>
          <div className="space-y-3"><div className="tal-skeleton h-4 w-28 rounded" /><div className="tal-skeleton h-12 w-full rounded" /></div>
        </div>
      ))}
    </div>
  );
}

function EvidenceList({ items, loadState, error, drafts, editingId, savingId, onEdit, onCancel, onDraft, onSave }: {
  items: EvidenceRead[];
  loadState: LoadState;
  error: string | null;
  drafts: Record<string, string>;
  editingId: string | null;
  savingId: string | null;
  onEdit: (item: EvidenceRead) => void;
  onCancel: () => void;
  onDraft: (id: string, value: string) => void;
  onSave: (item: EvidenceRead) => void;
}) {
  if (loadState === "loading") return <EvidenceSkeleton />;
  if (loadState === "error") return <div role="alert" className="rounded-[14px] border border-tal-red/25 bg-tal-red-soft p-5 text-sm text-tal-red">{error ?? "TAL could not load this résumé’s evidence. Refresh and try again."}</div>;
  if (loadState === "ready" && items.length === 0) return <div className="border-y border-tal-border py-10 text-center"><h2 className="text-lg font-semibold">No proof was found yet</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-tal-muted">Try a résumé version with clearer experience, project, or skill details.</p></div>;

  return (
    <ol className="divide-y divide-tal-border border-y border-tal-border">
      {items.map((item, index) => {
        const claim = item.corrected_text ?? item.extracted_text;
        const editing = editingId === item.id;
        const saving = savingId === item.id;
        const statusClass = item.status === "rejected" ? "bg-tal-red-soft text-tal-red" : item.status === "pending" ? "bg-tal-warning-soft text-tal-warning" : "bg-tal-green-soft text-tal-green";
        return (
          <li key={item.id} className="py-6">
            <div className="grid gap-4 md:grid-cols-[2rem_minmax(0,.9fr)_minmax(0,1.1fr)_auto] md:gap-6">
              <span className="flex size-8 items-center justify-center rounded-full bg-tal-ink text-sm font-semibold text-white">{index + 1}</span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full border border-tal-border px-2.5 py-1 text-xs font-medium text-tal-muted">{evidenceTypeLabel(item.evidence_type)}</span>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusClass}`}>{evidenceStatusLabel(item.status)}</span>
                </div>
                {editing ? (
                  <div className="mt-4">
                    <label htmlFor={`evidence-${item.id}`} className="text-sm font-semibold">Correct TAL’s claim</label>
                    <textarea id={`evidence-${item.id}`} value={drafts[item.id] ?? claim} onChange={(event) => onDraft(item.id, event.target.value)} rows={4} maxLength={2000} className="mt-2 min-h-28 w-full resize-y rounded-[12px] border border-tal-border-strong bg-white px-3 py-3 text-sm leading-6 outline-none focus:border-tal-ink" />
                    <p className="mt-2 text-xs leading-5 text-tal-muted">The correction changes TAL’s interpretation. The exact source quote stays unchanged.</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button type="button" onClick={() => onSave(item)} disabled={saving || !(drafts[item.id] ?? "").trim()} className="min-h-11 rounded-[10px] bg-tal-ink px-4 text-sm font-semibold text-white transition-colors hover:bg-tal-secondary disabled:cursor-not-allowed disabled:opacity-45">{saving ? "Saving correction…" : "Save correction"}</button>
                      <button type="button" onClick={onCancel} disabled={saving} className="min-h-11 rounded-[10px] px-4 text-sm font-semibold text-tal-muted transition-colors hover:bg-tal-subtle disabled:opacity-45">Keep original</button>
                    </div>
                  </div>
                ) : <p className="mt-4 text-base font-semibold leading-6">{claim}</p>}
                {item.canonical_skill_name && <p className="mt-3 text-xs text-tal-muted">Normalized skill: <span className="font-medium text-tal-secondary">{item.canonical_skill_name}</span></p>}
              </div>
              <blockquote className="min-w-0 border-t border-tal-border pt-4 text-sm leading-6 text-tal-secondary md:border-l md:border-t-0 md:pl-6 md:pt-0"><span className="mb-2 block text-xs font-semibold text-tal-ink">Exact source quote</span>“{item.source_text}”</blockquote>
              {!editing && <div className="md:self-start"><button type="button" onClick={() => onEdit(item)} className="flex min-h-11 items-center gap-2 rounded-[10px] border border-tal-border px-3 text-sm font-semibold text-tal-muted transition-colors hover:border-tal-border-strong hover:bg-tal-subtle hover:text-tal-ink" aria-label={`Correct evidence: ${claim}`}><PencilIcon /> Correct</button></div>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export default function ProofWorkspace() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const requestRef = useRef<XMLHttpRequest | null>(null);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [resume, setResume] = useState<ResumeRead | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [analysisOpen, setAnalysisOpen] = useState(true);
  const [evidence, setEvidence] = useState<EvidenceRead[]>([]);
  const [evidenceState, setEvidenceState] = useState<LoadState>("idle");
  const [evidenceFeedback, setEvidenceFeedback] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  useEffect(() => {
    const controller = new AbortController();
    async function loadUser() {
      try {
        const response = await fetch("/backend/api/v1/auth/me", { credentials: "include", signal: controller.signal });
        setUser(response.ok ? (await response.json()) as CurrentUser : null);
      } catch (caught) {
        if (!(caught instanceof DOMException && caught.name === "AbortError")) setUser(null);
      } finally {
        if (!controller.signal.aborted) setAuthLoading(false);
      }
    }
    void loadUser();
    return () => { controller.abort(); requestRef.current?.abort(); };
  }, []);

  useEffect(() => {
    if (!resume?.id || resume.status === "ready" || resume.status === "failed") return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let attempts = 0;
    async function poll() {
      if (attempts >= MAX_POLL_ATTEMPTS) {
        setFeedback("Analysis is taking longer than expected. Refresh shortly to check again.");
        return;
      }
      attempts += 1;
      try {
        const response = await fetch(`/backend/api/v1/resumes/${resume?.id}`, { credentials: "include", signal: controller.signal });
        if (!response.ok) {
          const data = (await response.json().catch(() => ({}))) as ApiError;
          throw new Error(apiMessage(data, "TAL could not check this résumé’s status."));
        }
        const nextResume = (await response.json()) as ResumeRead;
        setResume(nextResume);
        if (nextResume.status === "ready") {
          setFeedback("Analysis complete. Review every proof against its exact source.");
          return;
        }
        if (nextResume.status === "failed") {
          setError(true);
          setFeedback("TAL could not analyze this résumé. Start a new review and upload it again.");
          return;
        }
        setFeedback(nextResume.status === "processing" ? "TAL is finding proof and linking exact sources…" : "Your résumé is queued for analysis…");
        timer = setTimeout(() => void poll(), POLL_INTERVAL_MS);
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setError(true);
        setFeedback(caught instanceof Error ? caught.message : "TAL could not check this résumé’s status.");
      }
    }
    timer = setTimeout(() => void poll(), POLL_INTERVAL_MS);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [resume?.id, resume?.status]);

  useEffect(() => {
    if (!resume?.id || resume.status !== "ready") return;
    const controller = new AbortController();
    async function loadEvidence() {
      setEvidenceState("loading");
      try {
        const response = await fetch(`/backend/api/v1/resumes/${resume?.id}/evidence`, { credentials: "include", signal: controller.signal });
        if (!response.ok) {
          const data = (await response.json().catch(() => ({}))) as ApiError;
          throw new Error(apiMessage(data, "TAL could not load this résumé’s evidence."));
        }
        setEvidence((await response.json()) as EvidenceRead[]);
        setEvidenceState("ready");
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setEvidenceState("error");
        setEvidenceFeedback(caught instanceof Error ? caught.message : "TAL could not load this résumé’s evidence.");
      }
    }
    void loadEvidence();
    return () => controller.abort();
  }, [resume?.id, resume?.status]);

  function reset() {
    requestRef.current?.abort();
    setFile(null);
    setUploadProgress(0);
    setUploading(false);
    setResume(null);
    setFeedback(null);
    setError(false);
    setAnalysisOpen(true);
    setEvidence([]);
    setEvidenceState("idle");
    setEvidenceFeedback(null);
    setEditingId(null);
    setSavingId(null);
    setDrafts({});
  }

  function openPicker() {
    if (!authLoading && !user) {
      setError(true);
      setFeedback("Sign in before uploading a private résumé.");
      return;
    }
    fileInputRef.current?.click();
  }

  async function logout() {
    const response = await fetch("/backend/api/v1/auth/logout", { method: "POST", credentials: "include" });
    if (response.ok) { setUser(null); reset(); }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || uploading) return;
    setUploading(true);
    setError(false);
    setFeedback("Uploading your résumé securely…");
    setUploadProgress(0);
    const request = new XMLHttpRequest();
    requestRef.current = request;
    const body = new FormData();
    body.append("file", file);
    try {
      const result = await new Promise<{ status: number; data: ResumeRead | ApiError }>((resolve, reject) => {
        request.open("POST", "/backend/api/v1/resumes/");
        request.withCredentials = true;
        request.responseType = "json";
        request.upload.addEventListener("progress", (progress) => { if (progress.lengthComputable) setUploadProgress(Math.min(Math.round((progress.loaded / progress.total) * 100), 99)); });
        request.addEventListener("load", () => resolve({ status: request.status, data: (request.response ?? {}) as ResumeRead | ApiError }));
        request.addEventListener("error", () => reject(new Error("TAL could not reach the server. Check your connection and try again.")));
        request.addEventListener("abort", () => reject(new DOMException("Upload cancelled", "AbortError")));
        request.send(body);
      });
      if (result.status < 200 || result.status >= 300) throw new Error(apiMessage(result.data as ApiError, result.status === 401 ? "Sign in before uploading your résumé." : "TAL could not upload this résumé."));
      setUploadProgress(100);
      setResume(result.data as ResumeRead);
      setFile(null);
      setAnalysisOpen(true);
      setFeedback("Upload complete. TAL is preparing cited proof for your review.");
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") return;
      setError(true);
      setFeedback(caught instanceof Error ? caught.message : "TAL could not upload this résumé.");
    } finally {
      setUploading(false);
      requestRef.current = null;
    }
  }

  async function saveCorrection(item: EvidenceRead) {
    const correctedText = (drafts[item.id] ?? "").trim();
    if (!correctedText) return;
    setSavingId(item.id);
    setEvidenceFeedback(null);
    try {
      const response = await fetch(`/backend/api/v1/resumes/evidence/${item.id}`, { method: "PATCH", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ corrected_text: correctedText }) });
      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as ApiError;
        throw new Error(apiMessage(data, "TAL could not save this correction."));
      }
      const updated = (await response.json()) as EvidenceRead;
      setEvidence((items) => items.map((entry) => entry.id === updated.id ? updated : entry));
      setEditingId(null);
      setEvidenceFeedback("Correction saved. The original source quote remains unchanged.");
    } catch (caught) {
      setEvidenceFeedback(caught instanceof Error ? caught.message : "TAL could not save this correction.");
    } finally {
      setSavingId(null);
    }
  }

  const ready = resume?.status === "ready";
  return (
    <main className="flex min-h-dvh bg-tal-canvas text-tal-ink">
      <a href="#main-content" className="sr-only z-50 rounded-[8px] bg-tal-ink px-4 py-3 text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4">Skip to main content</a>
      <aside className="hidden w-64 shrink-0 flex-col bg-tal-ink px-4 py-5 text-white lg:flex">
        <Link href="/" className="flex min-h-11 items-center gap-3 px-2 text-lg font-bold tracking-[-0.02em]"><span className="grid size-8 place-items-center rounded-[9px] bg-tal-yellow text-sm font-black text-tal-ink">T</span>TAL</Link>
        <button type="button" onClick={reset} className="mt-7 flex min-h-12 items-center gap-3 rounded-[10px] bg-tal-yellow px-4 text-sm font-bold text-tal-ink transition-colors hover:bg-tal-yellow-hover"><PlusIcon /> New review</button>
        <nav className="mt-8 space-y-1" aria-label="Main navigation">
          <a href="#main-content" className="flex min-h-11 items-center gap-3 rounded-[10px] bg-white/10 px-3 text-sm font-semibold text-tal-yellow"><HomeIcon /> Home</a>
          <a href={ready ? "#evidence-review" : "#resume-workflow"} className="flex min-h-11 items-center gap-3 rounded-[10px] px-3 text-sm font-medium text-white/70 transition-colors hover:bg-white/[.06] hover:text-white"><DocumentIcon /> Proofs</a>
          <span aria-disabled="true" title="Applications arrive in a later TAL milestone" className="flex min-h-11 cursor-not-allowed items-center gap-3 rounded-[10px] px-3 text-sm font-medium text-white/35"><BriefcaseIcon /> Applications <span className="ml-auto text-[11px]">Later</span></span>
        </nav>
        <div className="mt-auto border-t border-white/10 pt-4">
          {user ? <div className="px-2 py-2"><p className="text-xs text-white/45">Signed in as</p><p className="mt-1 truncate text-sm font-medium" title={user.email}>{user.email}</p><button type="button" onClick={() => void logout()} className="mt-3 min-h-11 text-sm font-semibold text-white/65 hover:text-white">Log out</button></div> : <Link href="/login" className="flex min-h-11 items-center justify-between rounded-[10px] px-3 text-sm font-semibold text-white/75 hover:bg-white/[.06] hover:text-white">Sign in <span aria-hidden="true">→</span></Link>}
        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-16 items-center justify-between border-b border-tal-border bg-white px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex min-h-11 items-center gap-2 font-bold lg:hidden"><span className="grid size-8 place-items-center rounded-[9px] bg-tal-yellow text-sm font-black">T</span>TAL</Link>
          <p className="hidden text-sm font-semibold text-tal-secondary lg:block">Proof-led career workspace</p>
          {authLoading ? <div className="tal-skeleton h-10 w-28 rounded-[10px]" aria-label="Checking sign-in status" /> : user ? <div className="flex items-center gap-2"><span className="hidden max-w-52 truncate text-sm text-tal-secondary sm:block" title={user.email}>{user.email}</span><button type="button" onClick={() => void logout()} className="min-h-11 rounded-[10px] px-3 text-sm font-semibold text-tal-secondary hover:bg-tal-subtle lg:hidden">Log out</button></div> : <Link href="/login" className="flex min-h-11 items-center rounded-[10px] bg-tal-ink px-4 text-sm font-semibold text-white">Sign in</Link>}
        </header>

        <div id="main-content" className="flex-1" tabIndex={-1}>
          <div id="resume-workflow" className={`mx-auto w-full px-4 sm:px-6 lg:px-8 ${ready ? "max-w-6xl py-8 sm:py-12" : "max-w-4xl py-10 sm:py-16"}`}>
            {!resume ? (
              <section className="mx-auto flex min-h-[calc(100dvh-10rem)] max-w-3xl flex-col justify-center">
                <p className="text-sm font-semibold text-tal-secondary">Your résumé. Your evidence.</p>
                <h1 className="mt-4 max-w-2xl text-4xl font-black leading-[1.02] tracking-[-0.035em] text-balance sm:text-6xl">What do you want to prove?</h1>
                <p className="mt-5 max-w-xl text-base leading-7 text-tal-secondary text-pretty sm:text-lg">Attach your résumé when you want TAL to support career decisions with exact source quotes—not opaque scores.</p>
                <form onSubmit={upload} className="mt-10 rounded-[16px] bg-tal-ink p-3 text-white">
                  <input ref={fileInputRef} type="file" accept=".pdf,.docx" className="sr-only" aria-label="Attach a PDF or DOCX résumé" onChange={(event) => { const selected = event.target.files?.[0]; if (selected) { setFile(selected); setError(false); setFeedback(null); } event.target.value = ""; }} />
                  {file ? (
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                      <button type="button" onClick={openPicker} disabled={uploading} className="flex min-w-0 flex-1 items-center gap-3 rounded-[12px] bg-white/[.07] px-3 py-3 text-left hover:bg-white/10 disabled:cursor-default"><span className="flex size-10 shrink-0 items-center justify-center rounded-[9px] bg-white/10 text-tal-yellow">{uploading ? <span className="tal-working-ring size-6" /> : <DocumentIcon />}</span><span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold" title={file.name}>{file.name}</span><span className="mt-0.5 block text-xs text-white/50">{uploading ? `Uploading securely… ${uploadProgress}%` : file.name.toLowerCase().endsWith(".docx") ? "DOCX" : "PDF"}</span></span></button>
                      <div className="flex gap-2"><button type="button" onClick={() => setFile(null)} disabled={uploading} className="min-h-11 rounded-[10px] px-4 text-sm font-semibold text-white/65 hover:bg-white/[.06] hover:text-white disabled:opacity-40">Remove</button><button type="submit" disabled={uploading} className="min-h-11 flex-1 rounded-[10px] bg-tal-yellow px-5 text-sm font-bold text-tal-ink hover:bg-tal-yellow-hover disabled:cursor-wait disabled:opacity-60 sm:flex-none">{uploading ? "Uploading…" : "Analyze résumé"}</button></div>
                    </div>
                  ) : (
                    <button type="button" onClick={openPicker} disabled={authLoading} className="flex min-h-16 w-full items-center justify-between gap-4 rounded-[12px] bg-white/[.06] px-4 text-left hover:bg-white/10 disabled:cursor-wait disabled:opacity-60"><span className="flex items-center gap-3"><span className="flex size-10 items-center justify-center rounded-full bg-tal-yellow text-tal-ink"><PaperclipIcon /></span><span><span className="block text-sm font-semibold">{!authLoading && !user ? "Sign in to attach your résumé" : "Attach your résumé"}</span><span className="mt-1 block text-xs text-white/50">Private PDF or DOCX</span></span></span><span aria-hidden="true" className="text-lg text-white/45">→</span></button>
                  )}
                </form>
                <div aria-live="polite" className="min-h-10 px-2 pt-3">{feedback ? <p role={error ? "alert" : "status"} className={`text-sm ${error ? "text-tal-red" : "text-tal-secondary"}`}>{feedback}</p> : <p className="text-sm text-tal-muted">Your original file and every source quote stay unchanged.</p>}</div>
              </section>
            ) : ready ? (
              <section id="evidence-review" aria-labelledby="evidence-heading">
                <div className="flex flex-col gap-5 border-b border-tal-border pb-7 sm:flex-row sm:items-end sm:justify-between">
                  <div><p className="text-sm font-semibold text-tal-green">Analysis complete</p><h1 id="evidence-heading" className="mt-2 max-w-3xl text-3xl font-black tracking-[-0.03em] text-balance sm:text-5xl">Here’s what your résumé can prove.</h1><p className="mt-4 max-w-2xl text-sm leading-6 text-tal-secondary sm:text-base">Review TAL’s interpretation beside the exact source text. Correct a claim without changing the original résumé.</p></div>
                  <button type="button" onClick={reset} className="min-h-11 self-start rounded-[10px] bg-tal-yellow px-4 text-sm font-bold hover:bg-tal-yellow-hover sm:self-auto">Review another résumé</button>
                </div>
                <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]"><AnalysisPanel resume={resume} open={analysisOpen} onToggle={() => setAnalysisOpen((value) => !value)} /><ResumeFile resume={resume} /></div>
                <div className="mt-10">
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><p className="text-sm font-semibold text-tal-secondary">{evidence.length} {evidence.length === 1 ? "proof" : "proofs"} found</p><p className="text-xs text-tal-muted">Confidence scores stay hidden; sources stay visible.</p></div>
                  {evidenceFeedback && evidenceState !== "error" && <p role="status" className="mb-4 rounded-[10px] bg-tal-green-soft px-4 py-3 text-sm text-tal-green">{evidenceFeedback}</p>}
                  <EvidenceList items={evidence} loadState={evidenceState} error={evidenceFeedback} drafts={drafts} editingId={editingId} savingId={savingId} onEdit={(item) => { setEditingId(item.id); setDrafts((values) => ({ ...values, [item.id]: item.corrected_text ?? item.extracted_text })); }} onCancel={() => setEditingId(null)} onDraft={(id, value) => setDrafts((values) => ({ ...values, [id]: value }))} onSave={(item) => void saveCorrection(item)} />
                </div>
              </section>
            ) : (
              <section className="mx-auto max-w-3xl" aria-labelledby="processing-heading">
                <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-sm font-semibold text-tal-secondary">Résumé attached</p><h1 id="processing-heading" className="mt-2 text-3xl font-black tracking-[-0.03em] text-balance sm:text-5xl">TAL is finding proof.</h1><p className="mt-4 max-w-xl text-sm leading-6 text-tal-secondary sm:text-base">You can see the work that matters: status, what TAL is checking, and whether exact sources are linked.</p></div><button type="button" onClick={reset} className="min-h-11 self-start rounded-[10px] border border-tal-border px-4 text-sm font-semibold text-tal-secondary hover:border-tal-border-strong hover:bg-tal-subtle">Cancel review</button></div>
                <ResumeFile resume={resume} />
                <div className="mt-4"><AnalysisPanel resume={resume} open={analysisOpen} onToggle={() => setAnalysisOpen((value) => !value)} /></div>
                {feedback && <p role={error ? "alert" : "status"} className={`mt-4 rounded-[10px] px-4 py-3 text-sm ${error ? "bg-tal-red-soft text-tal-red" : "bg-tal-subtle text-tal-secondary"}`}>{feedback}</p>}
              </section>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
