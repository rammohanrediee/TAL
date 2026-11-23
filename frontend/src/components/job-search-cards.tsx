"use client";

import { ArrowUpRight } from "lucide-react";

export type JobFitCard = {
  id: string;
  title: string;
  company_name: string;
  location: string | null;
  work_mode: string | null;
  fit_score: number | null;
  matched_skills: string[];
  job_url: string;
  apply_url: string;
  validation_status: "ok" | "thin_description";
};

function formatFit(score: number | null): string {
  if (score === null) return "—";
  return `${score.toFixed(1)}/5`;
}

export default function JobSearchCards({ jobs }: { jobs: JobFitCard[] }) {
  if (jobs.length === 0) return null;
  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-bold uppercase tracking-wide text-tal-secondary">Job matches</p>
      <ul className="space-y-2">
        {jobs.map((job) => (
          <li
            key={job.id}
            className="rounded-[12px] border border-tal-border bg-tal-surface p-3 shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-bold text-tal-ink">{job.title}</p>
                <p className="text-sm text-tal-secondary">
                  {job.company_name}
                  {job.location ? ` · ${job.location}` : ""}
                  {job.work_mode ? ` · ${job.work_mode}` : ""}
                </p>
              </div>
              <span
                className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-black ${
                  job.validation_status === "thin_description"
                    ? "bg-tal-warning-soft text-tal-warning"
                    : "bg-tal-yellow text-tal-ink"
                }`}
              >
                {formatFit(job.fit_score)}
              </span>
            </div>
            {job.matched_skills.length > 0 && (
              <ul className="mt-2 flex flex-wrap gap-1.5" aria-label="Matched skills">
                {job.matched_skills.slice(0, 6).map((skill) => (
                  <li key={skill}>
                    <span className="rounded-full border border-tal-border bg-tal-subtle px-2 py-0.5 text-xs font-semibold text-tal-secondary">
                      {skill}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {job.validation_status === "thin_description" && (
              <p className="mt-1 text-xs text-tal-muted">Limited job description — score capped.</p>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-4">
              <a
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm font-bold text-tal-ink hover:underline"
              >
                Apply <ArrowUpRight size={14} aria-hidden />
              </a>
              <a
                href={job.job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-semibold text-tal-secondary hover:text-tal-ink hover:underline"
              >
                View posting
              </a>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function jobsFromToolPayload(payload: unknown): JobFitCard[] | null {
  if (!payload || typeof payload !== "object") return null;
  const data = payload as Record<string, unknown>;
  const jobs = data.jobs;
  if (!Array.isArray(jobs)) return null;
  return jobs as JobFitCard[];
}

export function extractJobSearchFromMessageParts(parts: unknown[]): JobFitCard[] | null {
  for (const part of parts) {
    if (!part || typeof part !== "object") continue;
    const record = part as Record<string, unknown>;
    const type = String(record.type ?? "");
    const toolName = String(record.toolName ?? record.tool_name ?? "");
    const isSearchTool =
      toolName === "search_jobs" || type === "tool-search_jobs" || type.includes("search_jobs");
    if (!isSearchTool) continue;
    const fromOutput = jobsFromToolPayload(record.output ?? record.result);
    if (fromOutput) return fromOutput;
  }

  for (const part of parts) {
    if (!part || typeof part !== "object") continue;
    const record = part as Record<string, unknown>;
    const type = String(record.type ?? "");
    if (!type.startsWith("tool-") || !type.includes("search_jobs")) continue;
    const state = record.state ?? record.toolState;
    if (state && state !== "output-available" && state !== "result") continue;
    const fromOutput = jobsFromToolPayload(record.output ?? record.result);
    if (fromOutput) return fromOutput;
  }
  return null;
}