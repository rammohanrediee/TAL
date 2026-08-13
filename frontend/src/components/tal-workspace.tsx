"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";

type ComposerState = "idle" | "uploading" | "success" | "error";
type ResumeStatus = "uploaded" | "processing" | "ready" | "failed";

interface ResumeRead {
  id: string;
  original_filename: string;
  status: ResumeStatus;
}

interface ApiError {
  message?: string;
}

interface CurrentUser {
  id: string;
  email: string;
}

const RESUME_POLL_INTERVAL_MS = 1_000;
const RESUME_POLL_MAX_ATTEMPTS = 30;
const PROCESSING_PROGRESS_START = 30;
const PROCESSING_PROGRESS_CAP = 90;
const PROCESSING_PROGRESS_STEP_MS = 400;

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="size-5" aria-hidden="true">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function PaperclipIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="size-5" aria-hidden="true">
      <path
        d="m9.5 12.5 5.4-5.4a3 3 0 0 1 4.2 4.2l-7.5 7.5a5 5 0 0 1-7.1-7.1l7.2-7.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      className="size-5"
      aria-hidden="true"
    >
      <path
        d="m5 12 4.5 4.5L19 7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DocumentIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      className="size-5"
      aria-hidden="true"
    >
      <path
        d="M7 3h7l4 4v14H7z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M14 3v5h5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

interface ProgressRingProps {
  value: number;
  className?: string;
  labelClassName?: string;
}

function ProgressRing({
  value,
  className = "size-10",
  labelClassName = "text-[9px]",
}: ProgressRingProps) {
  return (
    <span
      role="img"
      aria-label={`Progress: ${value}%`}
      className={`relative flex items-center justify-center ${className}`}
    >
      <svg
        viewBox="0 0 40 40"
        className="absolute inset-0 size-full -rotate-90"
        aria-hidden="true"
      >
        <circle
          cx="20"
          cy="20"
          r="17"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          className="text-action/20"
        />
        <circle
          cx="20"
          cy="20"
          r="17"
          pathLength="100"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray="100"
          strokeDashoffset={100 - value}
          className="text-action transition-[stroke-dashoffset] duration-300 ease-out motion-reduce:transition-none"
        />
      </svg>
      <span className={`font-semibold tabular-nums text-ink ${labelClassName}`}>
        {value}%
      </span>
    </span>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="size-5" aria-hidden="true">
      <path d="M12 19V5M6 11l6-6 6 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function TalWorkspace() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadRequestRef = useRef<XMLHttpRequest | null>(null);
  const uploadCompletionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [message, setMessage] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [composerState, setComposerState] = useState<ComposerState>("idle");
  const [uploadedResume, setUploadedResume] = useState<ResumeRead | null>(null);
  const [processingProgress, setProcessingProgress] = useState(PROCESSING_PROGRESS_START);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [attachmentMenuOpen, setAttachmentMenuOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    async function loadCurrentUser() {
      try {
        const response = await fetch("/backend/api/v1/auth/me", {
          credentials: "include",
          signal: controller.signal,
        });

        if (!response.ok) {
          setCurrentUser(null);
          return;
        }

        setCurrentUser((await response.json()) as CurrentUser);
      } catch (error: unknown) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setCurrentUser(null);
        }
      } finally {
        if (!controller.signal.aborted) {
          setAuthLoading(false);
        }
      }
    }

    void loadCurrentUser();

    return () => {
      controller.abort();
      uploadRequestRef.current?.abort();

      if (uploadCompletionTimerRef.current !== null) {
        clearTimeout(uploadCompletionTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const resumeId = uploadedResume?.id;

    if (!resumeId) {
      return;
    }

    const controller = new AbortController();
    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;

    async function pollResumeStatus() {
      if (attempts >= RESUME_POLL_MAX_ATTEMPTS) {
        setFeedback(
          "Processing is taking longer than expected. Check again shortly.",
        );
        return;
      }

      attempts += 1;

      try {
        const response = await fetch(
          `/backend/api/v1/resumes/${resumeId}`,
          {
            credentials: "include",
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          if (response.status === 401) {
            setCurrentUser(null);
            throw new Error(
              "Your session expired. Sign in to check this résumé.",
            );
          }

          throw new Error("TAL could not check your résumé status.");
        }

        const resume = (await response.json()) as ResumeRead;

        if (controller.signal.aborted) {
          return;
        }

        setUploadedResume(resume);

        if (resume.status === "ready") {
          setComposerState("success");
          setFeedback(
            "Evidence extraction is complete. Your résumé is ready for review.",
          );
          return;
        }

        if (resume.status === "failed") {
          setComposerState("error");
          setFeedback(
            "TAL could not process this résumé. Try uploading it again.",
          );
          return;
        }

        setFeedback(
          resume.status === "processing"
            ? "TAL is extracting evidence from your résumé…"
            : "Your résumé is waiting to be processed…",
        );

        timeoutId = setTimeout(
          () => void pollResumeStatus(),
          RESUME_POLL_INTERVAL_MS,
        );
      } catch (error: unknown) {
        if (
          error instanceof DOMException &&
          error.name === "AbortError"
        ) {
          return;
        }

        setComposerState("error");
        setFeedback(
          error instanceof Error
            ? error.message
            : "TAL could not check your résumé status.",
        );
      }
    }

    timeoutId = setTimeout(
      () => void pollResumeStatus(),
      RESUME_POLL_INTERVAL_MS,
    );

    return () => {
      controller.abort();

      if (timeoutId !== undefined) {
        clearTimeout(timeoutId);
      }
    };
  }, [uploadedResume?.id]);

  useEffect(() => {
    if (uploadedResume?.status !== "processing") {
      return;
    }

    // No real per-stage progress exists on the backend, so animate a bounded
    // climb from the queued stage. It never reaches 100% here — that is only
    // shown when the backend reports the résumé as ready. The starting value
    // is seeded when each upload begins, so this effect never sets state
    // synchronously.
    const intervalId = setInterval(() => {
      setProcessingProgress((progress) =>
        Math.min(progress + 2, PROCESSING_PROGRESS_CAP),
      );
    }, PROCESSING_PROGRESS_STEP_MS);

    return () => clearInterval(intervalId);
  }, [uploadedResume?.status]);

  const canSubmit =
    (Boolean(message.trim()) || selectedFile !== null) &&
    composerState !== "uploading" &&
    !(selectedFile && uploadProgress === 100);

  function openFilePicker() {
    setAttachmentMenuOpen(false);
    fileInputRef.current?.click();
  }

  function startNewConversation() {
    uploadRequestRef.current?.abort();
    uploadRequestRef.current = null;

    if (uploadCompletionTimerRef.current !== null) {
      clearTimeout(uploadCompletionTimerRef.current);
      uploadCompletionTimerRef.current = null;
    }

    setMessage("");
    setSelectedFile(null);
    setUploadProgress(0);
    setComposerState("idle");
    setUploadedResume(null);
    setProcessingProgress(PROCESSING_PROGRESS_START);
    setFeedback(null);
    setAttachmentMenuOpen(false);
  }

  function removeSelectedFile() {
    uploadRequestRef.current?.abort();
    uploadRequestRef.current = null;

    if (uploadCompletionTimerRef.current !== null) {
      clearTimeout(uploadCompletionTimerRef.current);
      uploadCompletionTimerRef.current = null;
    }

    setSelectedFile(null);
    setUploadProgress(0);
    setComposerState("idle");
    setProcessingProgress(PROCESSING_PROGRESS_START);
    setFeedback(null);
  }

  async function handleLogout() {
    const response = await fetch("/backend/api/v1/auth/logout", {
      method: "POST",
      credentials: "include",
    });

    if (response.ok) {
      setCurrentUser(null);
      startNewConversation();
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      setComposerState("error");
      setFeedback(
        "Text chat is the next integration milestone. Attach a résumé to test the live upload flow.",
      );
      return;
    }

    setComposerState("uploading");
    setFeedback("Uploading your résumé securely…");
    setUploadedResume(null);
    setProcessingProgress(PROCESSING_PROGRESS_START);
    setUploadProgress(0);

    const request = new XMLHttpRequest();
    uploadRequestRef.current = request;

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await new Promise<{
        status: number;
        data: ResumeRead | ApiError;
      }>((resolve, reject) => {
        request.open("POST", "/backend/api/v1/resumes/");
        request.withCredentials = true;
        request.responseType = "json";

        request.upload.addEventListener("progress", (progressEvent) => {
          if (!progressEvent.lengthComputable) {
            return;
          }

          const percentage = Math.round(
            (progressEvent.loaded / progressEvent.total) * 100,
          );
          setUploadProgress(Math.min(percentage, 99));
        });

        request.addEventListener("load", () => {
          resolve({
            status: request.status,
            data: (request.response ?? {}) as ResumeRead | ApiError,
          });
        });
        request.addEventListener("error", () => {
          reject(new Error("TAL could not connect to the server."));
        });
        request.addEventListener("abort", () => {
          reject(new DOMException("Upload cancelled", "AbortError"));
        });

        request.send(formData);
      });

      if (response.status < 200 || response.status >= 300) {
        const apiError = response.data as ApiError;
        if (response.status === 401) {
          throw new Error("Sign in before uploading your résumé.");
        }
        throw new Error(apiError.message ?? "TAL could not upload your résumé.");
      }

      const resume = response.data as ResumeRead;
      setUploadProgress(100);
      setUploadedResume(resume);
      setComposerState("success");
      setFeedback("Upload complete. TAL queued this résumé for evidence extraction.");

      uploadCompletionTimerRef.current = setTimeout(() => {
        setSelectedFile(null);
        setUploadProgress(0);
        setMessage("");
        uploadCompletionTimerRef.current = null;
      }, 800);
    } catch (error: unknown) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      setUploadProgress(0);
      setComposerState("error");
      setFeedback(
        error instanceof Error ? error.message : "TAL could not connect to the server.",
      );
    } finally {
      if (uploadRequestRef.current === request) {
        uploadRequestRef.current = null;
      }
    }
  }

  const resumeProgress = uploadedResume
    ? uploadedResume.status === "ready"
      ? 100
      : uploadedResume.status === "failed"
        ? 0
        : uploadedResume.status === "processing"
          ? processingProgress
          : PROCESSING_PROGRESS_START
    : 0;

  return (
    <main className="flex min-h-dvh bg-canvas text-ink">
      <aside className="hidden w-66 shrink-0 flex-col border-r border-border bg-surface-subtle p-3 md:flex">
        <div className="flex h-12 items-center gap-3 px-2">
          <span className="flex size-8 items-center justify-center rounded-[10px] bg-action font-display text-lg text-on-action">T</span>
          <span className="font-semibold tracking-tight">TAL</span>
        </div>

        <button
          type="button"
          onClick={startNewConversation}
          className="mt-4 flex min-h-11 items-center gap-3 rounded-[10px] border border-border bg-surface px-3 text-left text-sm font-semibold transition-colors hover:border-border-strong hover:bg-canvas"
        >
          <PlusIcon />
          New conversation
        </button>

        <div className="mt-auto border-t border-border pt-3">
          {currentUser ? (
            <div className="min-w-0 rounded-[10px] px-3 py-2">
              <p className="text-xs text-ink-muted">Signed in as</p>
              <p className="truncate text-sm font-medium text-ink" title={currentUser.email}>
                {currentUser.email}
              </p>
            </div>
          ) : (
            <Link href="/login" className="flex min-h-11 items-center justify-between rounded-[10px] px-3 text-sm text-ink-secondary hover:bg-surface-strong hover:text-ink">
              <span>Account</span><span aria-hidden="true">→</span>
            </Link>
          )}
        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-border px-4 md:border-b-0 md:px-7">
          <Link href="/" className="flex items-center gap-2 font-semibold md:hidden">
            <span className="flex size-8 items-center justify-center rounded-[10px] bg-action text-on-action">T</span>
            TAL
          </Link>
          <p className="hidden text-sm font-medium text-ink-secondary md:block">Career workspace</p>
          {authLoading ? (
            <div className="h-11 w-32" aria-label="Checking sign-in status" />
          ) : currentUser ? (
            <div className="flex items-center gap-2">
              <span className="hidden max-w-56 truncate text-sm text-ink-secondary sm:block" title={currentUser.email}>
                {currentUser.email}
              </span>
              <button
                type="button"
                onClick={() => void handleLogout()}
                className="flex min-h-11 items-center rounded-[10px] px-4 text-sm font-semibold text-ink-secondary hover:bg-surface-subtle hover:text-ink"
              >
                Log out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link href="/login" className="flex min-h-11 items-center rounded-[10px] px-4 text-sm font-semibold text-ink-secondary hover:bg-surface-subtle hover:text-ink">Log in</Link>
              <Link href="/login" className="hidden min-h-11 items-center rounded-[10px] bg-ink px-4 text-sm font-semibold text-canvas sm:flex">Get started</Link>
            </div>
          )}
        </header>

        <div className="flex flex-1 flex-col px-4 pb-5 sm:px-6">
          <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center py-10 sm:pb-28 sm:pt-12">
            <div className="text-center">
              <h1 className="font-display text-3xl font-normal leading-tight tracking-[-0.02em] sm:text-4xl">
                Let’s build your next move.
              </h1>
            </div>

            {uploadedResume && !selectedFile && (
              <article
                aria-live="polite"
                className={`mx-auto mt-6 flex min-h-28 w-full max-w-2xl items-center rounded-[20px] border px-5 py-4 text-left ${
                  uploadedResume.status === "ready"
                    ? "border-success/25 bg-success-soft"
                    : uploadedResume.status === "failed"
                      ? "border-danger/25 bg-danger-soft"
                      : "border-border bg-surface-subtle"
                }`}
              >
                <div className="flex items-start gap-3">
                  <span
                    aria-hidden="true"
                    className={`flex size-14 shrink-0 items-center justify-center rounded-[14px] ${
                      uploadedResume.status === "ready"
                        ? "bg-success text-white"
                        : uploadedResume.status === "failed"
                          ? "bg-danger text-white"
                          : "bg-surface text-action"
                    }`}
                  >
                    {uploadedResume.status === "ready" ? (
                      "✓"
                    ) : uploadedResume.status === "failed" ? (
                      "!"
                    ) : (
                      <ProgressRing
                        value={resumeProgress}
                        className="size-12"
                        labelClassName="text-[11px]"
                      />
                    )}
                  </span>
                  <div className="min-w-0">
                    <p
                      className="truncate text-base font-semibold text-ink"
                      title={uploadedResume.original_filename}
                    >
                      {uploadedResume.original_filename}
                    </p>
                    <p className="mt-1 text-sm text-ink-muted">
                      {uploadedResume.status === "ready"
                        ? "Ready for review"
                        : uploadedResume.status === "failed"
                          ? "Processing failed"
                          : uploadedResume.status === "processing"
                            ? "Extracting résumé evidence…"
                            : "Queued for processing…"}
                    </p>
                  </div>
                </div>
              </article>
            )}
            <div className="mt-8 w-full">
            <form onSubmit={handleSubmit} className="rounded-[18px] border border-border bg-surface p-2 shadow-[0_8px_28px_rgba(25,24,22,0.08)]">
              {selectedFile && (
                <div className="relative mx-1 mb-3 w-full max-w-80">
                  <button
                    type="button"
                    aria-label={`Replace ${selectedFile.name}`}
                    onClick={openFilePicker}
                    disabled={composerState === "uploading"}
                    className="tal-file-tile grid h-[72px] w-full min-w-0 grid-cols-[2.5rem_minmax(0,1fr)] items-center gap-3 border border-border-strong bg-surface px-3 py-2 text-left transition-colors hover:bg-surface-subtle disabled:cursor-default"
                  >
                    <span
                      className={`flex size-10 shrink-0 items-center justify-center rounded-[10px] ${
                        uploadProgress === 100
                          ? "bg-success-soft text-success"
                          : "bg-surface-subtle text-action"
                      }`}
                    >
                      {uploadProgress === 100 ? (
                        <CheckIcon />
                      ) : composerState === "uploading" ? (
                        <ProgressRing value={uploadProgress} />
                      ) : (
                        <DocumentIcon />
                      )}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold" title={selectedFile.name}>
                        {selectedFile.name}
                      </span>
                      <span className="mt-0.5 block text-xs text-ink-muted">
                        {uploadProgress === 100
                          ? "Upload complete"
                          : composerState === "uploading"
                            ? `Uploading securely… ${uploadProgress}%`
                          : selectedFile.name.toLowerCase().endsWith(".docx")
                            ? "DOCX"
                            : "PDF"}
                      </span>
                    </span>
                  </button>
                  <button
                    type="button"
                    aria-label={`${composerState === "uploading" ? "Cancel upload of" : "Remove"} ${selectedFile.name}`}
                    onClick={removeSelectedFile}
                    className="absolute -right-3 -top-3 z-10 flex size-11 items-center justify-center rounded-full text-xl text-ink-secondary"
                  >
                    <span className="flex size-8 items-center justify-center rounded-full border border-border bg-surface text-ink shadow-[0_1px_3px_rgba(25,24,22,0.12)] transition-colors hover:bg-surface-strong">
                      ×
                    </span>
                  </button>
                </div>
              )}

              <div className="flex items-end gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx"
                  className="sr-only"
                  aria-label="Attach a PDF or DOCX résumé"
                  onChange={(event) => {
                    const file = event.target.files?.[0] ?? null;
                    setSelectedFile(file);
                    setUploadProgress(0);
                    setComposerState("idle");
                    setFeedback(null);
                    setUploadedResume(null);
                    event.target.value = "";
                  }}
                />
                <div className="relative shrink-0">
                  {attachmentMenuOpen && (
                    <div
                      role="menu"
                      aria-label="Attachment options"
                      className="absolute left-0 top-14 z-20 w-64 rounded-[14px] border border-border bg-surface p-1.5 shadow-[0_8px_28px_rgba(25,24,22,0.12)]"
                      onKeyDown={(event) => {
                        if (event.key === "Escape") {
                          setAttachmentMenuOpen(false);
                        }
                      }}
                    >
                      <button
                        type="button"
                        role="menuitem"
                        onClick={openFilePicker}
                        className="flex min-h-12 w-full items-center gap-3 rounded-[10px] px-3 text-left text-sm font-medium text-ink transition-colors hover:bg-surface-subtle"
                      >
                        <PaperclipIcon />
                        <span>
                          <span className="block">Add résumé or file</span>
                          <span className="mt-0.5 block text-xs font-normal text-ink-muted">
                            PDF or DOCX
                          </span>
                        </span>
                      </button>
                    </div>
                  )}

                  <button
                    type="button"
                    aria-label="Open attachment menu"
                    aria-haspopup="menu"
                    aria-expanded={attachmentMenuOpen}
                    title="Add an attachment"
                    onClick={() => setAttachmentMenuOpen((open) => !open)}
                    disabled={composerState === "uploading"}
                    className="flex size-11 items-center justify-center rounded-[10px] text-ink-secondary transition-colors hover:bg-surface-subtle hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <PlusIcon />
                  </button>
                </div>

                <label htmlFor="tal-message" className="sr-only">Message TAL</label>
                <textarea
                  id="tal-message"
                  rows={1}
                  value={message}
                  onChange={(event) => {
                    setMessage(event.target.value);
                    setComposerState("idle");
                    setFeedback(null);
                  }}
                  placeholder="Ask TAL about your career…"
                  className="tal-composer-input max-h-40 min-h-11 flex-1 resize-none bg-transparent px-1 py-2.5 text-[15px] leading-6 text-ink outline-none placeholder:text-ink-muted"
                />

                <button type="submit" aria-label={selectedFile ? "Upload résumé" : "Send message"} disabled={!canSubmit} className="flex size-11 shrink-0 items-center justify-center rounded-[10px] bg-action text-on-action transition-colors hover:bg-action-hover disabled:cursor-not-allowed disabled:bg-surface-strong disabled:text-ink-muted">
                  {composerState === "uploading" ? <span className="text-xs font-semibold">…</span> : <SendIcon />}
                </button>
              </div>
            </form>

            <div aria-live="polite" className="min-h-9 px-2 pt-2 text-center">
              {feedback && (
                <p role={composerState === "error" ? "alert" : "status"} className={`text-xs ${composerState === "error" ? "text-danger" : "text-ink-muted"}`}>{feedback}</p>
              )}
            </div>
            </div>
          </div>
          <p className="shrink-0 pb-1 text-center text-xs text-ink-muted">
            TAL can make mistakes. Check important information.
          </p>
        </div>
      </section>
    </main>
  );
}
