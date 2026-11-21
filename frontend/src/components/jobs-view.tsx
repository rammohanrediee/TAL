"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, RefreshCw, Search, X } from "lucide-react";
import styles from "./jobs-view.module.css";

type Board = { id: string; provider: string; company_name: string; board_url: string; last_scanned_at: string | null; last_error: string | null };
type Job = { id: string; company_name: string; provider: string; title: string; location: string | null; work_mode: string | null; employment_type: string | null; description: string | null; job_url: string; apply_url: string; last_verified_at: string };
type Scan = { board_id: string; status: string; found_count: number; error: string | null };
const PAGE_SIZE = 50;

async function jobsApi(path: string, init?: RequestInit) {
  const response = await fetch(`/backend/api/v1/jobs${path}`, { credentials: "include", ...init });
  if (!response.ok) {
    const data = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(data.detail || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

function dateLabel(value: string | null) {
  return value ? new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "Not scanned";
}

export default function JobsView() {
  const [boards, setBoards] = useState<Board[]>([]);
  const [catalog, setCatalog] = useState<Board[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [moreLoading, setMoreLoading] = useState(false);
  const [boardUrl, setBoardUrl] = useState("");
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [workMode, setWorkMode] = useState("");
  const [company, setCompany] = useState("");
  const [sinceDays, setSinceDays] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scanResult, setScanResult] = useState("");

  const refresh = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (query) params.set("query", query);
      if (location) params.set("location", location);
      if (workMode) params.set("work_mode", workMode);
      if (company) params.set("company", company);
      if (sinceDays) params.set("since_days", sinceDays);
      const [nextBoards, nextCatalog, nextJobs] = await Promise.all([
        jobsApi("/boards") as Promise<Board[]>,
        jobsApi("/catalog") as Promise<Board[]>,
        jobsApi(params.size ? `?${params.toString()}` : "") as Promise<Job[]>,
      ]);
      setBoards(nextBoards);
      setCatalog(nextCatalog);
      setJobs(nextJobs.slice(0, PAGE_SIZE));
      setHasMore(nextJobs.length > PAGE_SIZE);
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load jobs.");
    } finally {
      setLoading(false);
    }
  }, [query, location, workMode, company, sinceDays]);

  useEffect(() => { const timer = setTimeout(() => { void refresh(); }, 220); return () => clearTimeout(timer); }, [refresh]);

  async function loadMore() {
    setMoreLoading(true);
    try {
      const params = new URLSearchParams({ offset: String(jobs.length) });
      if (query) params.set("query", query);
      if (location) params.set("location", location);
      if (workMode) params.set("work_mode", workMode);
      if (company) params.set("company", company);
      if (sinceDays) params.set("since_days", sinceDays);
      const nextJobs = await jobsApi(`?${params.toString()}`) as Job[];
      setJobs((current) => [...current, ...nextJobs.slice(0, PAGE_SIZE)]);
      setHasMore(nextJobs.length > PAGE_SIZE);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load more jobs.");
    } finally { setMoreLoading(false); }
  }

  async function addBoard(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(""); setScanResult("");
    try {
      await jobsApi("/boards", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ board_url: boardUrl }) });
      setBoardUrl("");
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not add board.");
    } finally { setBusy(false); }
  }

  async function scan() {
    setBusy(true); setError(""); setScanResult("");
    try {
      const result = await jobsApi("/scan", { method: "POST" }) as Scan[];
      const success = result.filter((item) => item.status === "success");
      const failed = result.filter((item) => item.status === "failed");
      const skipped = result.filter((item) => item.status === "skipped");
      setScanResult(`${success.length} board${success.length === 1 ? "" : "s"} scanned · ${success.reduce((sum, item) => sum + item.found_count, 0)} jobs found${skipped.length ? ` · ${skipped.length} recently scanned` : ""}${failed.length ? ` · ${failed.length} failed` : ""}`);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Scan failed.");
    } finally { setBusy(false); }
  }

  async function removeBoard(id: string) {
    setBusy(true); setError("");
    try {
      await jobsApi(`/boards/${id}`, { method: "DELETE" });
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not remove board.");
    } finally { setBusy(false); }
  }

  return <div className={styles.page}>
    <header className={styles.header}>
      <div><p className={styles.eyebrow}>TAL / Opportunities</p><h1>Live roles, ready to explore.</h1><p>Browse public openings from company career boards. TAL checks the shared feed daily.</p></div>
      {boards.length > 0 && <button type="button" onClick={() => void scan()} disabled={busy} className={styles.scanButton}><RefreshCw size={16} aria-hidden="true" />{busy ? "Working…" : "Refresh watched"}</button>}
    </header>
    <div className={styles.body}>
      {error && <p role="alert" className={styles.error}>{error}</p>}
      {scanResult && <p role="status" className={styles.success}>{scanResult}</p>}
      <section className={styles.watchPanel} aria-labelledby="watch-heading">
        <div className={styles.sectionTitle}><h2>Public sources</h2><span>{catalog.length}</span></div>
        <p className={styles.sourceIntro}>Open roles from these company boards appear for every signed-in user.</p>
        {catalog.length > 0 && <div className={styles.sourceList}>{catalog.map((board) => <a key={board.id} href={board.board_url} target="_blank" rel="noopener noreferrer">{board.company_name}<ArrowUpRight size={13} aria-hidden="true" /></a>)}</div>}
        <div className={styles.sectionTitle}><h2 id="watch-heading">Watch another board</h2><span>{boards.length}</span></div>
        <form onSubmit={(event) => void addBoard(event)} className={styles.addForm}>
          <label htmlFor="board-url">Company board URL</label>
          <div><input id="board-url" type="url" required placeholder="https://jobs.ashbyhq.com/company" value={boardUrl} onChange={(event) => setBoardUrl(event.target.value)} /><button type="submit" disabled={busy}>Add board</button></div>
          <p>Greenhouse, Lever, and Ashby public boards are supported.</p>
        </form>
        {loading ? <p className={styles.empty}>Loading boards…</p> : boards.length === 0 ? null : <ul className={styles.boardList}>{boards.map((board) => <li key={board.id}>
          <div><strong>{board.company_name}</strong><span>{board.provider} · {dateLabel(board.last_scanned_at)}</span>{board.last_error && <small role="status">Last scan failed: {board.last_error}</small>}</div>
          <button type="button" aria-label={`Stop watching ${board.company_name}`} title="Stop watching" onClick={() => void removeBoard(board.id)} disabled={busy}><X size={17} /></button>
        </li>)}</ul>}
      </section>
      <section className={styles.results} aria-labelledby="results-heading">
        <div className={styles.sectionTitle}><h2 id="results-heading">Open roles</h2><span>{jobs.length}</span></div>
        <div className={styles.filters}>
          <label><Search size={16} aria-hidden="true" /><span className={styles.srOnly}>Search roles</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Role or company" /></label>
          <label><span className={styles.srOnly}>Location</span><input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Location" /></label>
          <label><span className={styles.srOnly}>Work mode</span><select value={workMode} onChange={(event) => setWorkMode(event.target.value)}><option value="">Any work mode</option><option value="Remote">Remote</option><option value="Hybrid">Hybrid</option><option value="Onsite">On-site</option></select></label>
          <label><span className={styles.srOnly}>Company</span><select value={company} onChange={(event) => setCompany(event.target.value)}><option value="">Any company</option>{[...new Map([...catalog, ...boards].map((board) => [board.id, board])).values()].map((board) => <option key={board.id} value={board.company_name}>{board.company_name}</option>)}</select></label>
          <label><span className={styles.srOnly}>Freshness</span><select value={sinceDays} onChange={(event) => setSinceDays(event.target.value)}><option value="">Any date</option><option value="7">New this week</option><option value="30">New this month</option></select></label>
        </div>
        {loading ? <p className={styles.empty}>Loading jobs…</p> : jobs.length === 0 ? <p className={styles.empty}>No matching live jobs. Try a different search or check back after the next scan.</p> : <div className={styles.jobList}>{jobs.map((job) => <article key={job.id} className={styles.jobCard}>
          <div><p className={styles.company}>{job.company_name}</p><h3>{job.title}</h3><p className={styles.meta}>{[job.location, job.work_mode, job.employment_type].filter(Boolean).join(" · ") || "Location not listed"}</p><p className={styles.verified}>Verified {dateLabel(job.last_verified_at)} · {job.provider}</p></div>
          <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className={styles.openLink}>Open application <ArrowUpRight size={16} aria-hidden="true" /></a>
        </article>)}{hasMore && <button type="button" className={styles.moreButton} onClick={() => void loadMore()} disabled={moreLoading}>{moreLoading ? "Loading…" : "Load more roles"}</button>}</div>}
      </section>
    </div>
  </div>;
}
