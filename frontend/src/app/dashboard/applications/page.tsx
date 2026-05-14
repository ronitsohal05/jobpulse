"use client";

import { Suspense, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ClipboardList, ExternalLink, Trash2 } from "lucide-react";
import { api, type ApplicationOut } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const STATUSES = [
  "interested",
  "applied",
  "screening",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
] as const;

function statusStyle(s: string) {
  switch (s) {
    case "offer":
      return "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-100";
    case "rejected":
    case "withdrawn":
      return "border-zinc-300 bg-zinc-100 text-zinc-800 dark:border-zinc-600 dark:bg-zinc-900 dark:text-zinc-200";
    case "interview":
      return "border-violet-300 bg-violet-50 text-violet-900 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-100";
    case "applied":
    case "screening":
      return "border-amber-200 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100";
    default:
      return "border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-800 dark:bg-sky-950/30 dark:text-sky-100";
  }
}

function ApplicationsInner() {
  const sp = useSearchParams();
  const prefillJobId = sp.get("job_id") || "";

  const [rows, setRows] = useState<ApplicationOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterResume, setFilterResume] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [jobPostingId, setJobPostingId] = useState("");
  const [resumeId, setResumeId] = useState("");
  const [status, setStatus] = useState<string>("interested");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  async function fetchList() {
    setLoading(true);
    setError(null);
    try {
      const list = await api.applications.list({
        resume_id: filterResume.trim() || undefined,
        status: filterStatus || undefined,
        limit: 150,
      });
      setRows(list);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load applications");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchList();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial load only
  }, []);

  useEffect(() => {
    if (!prefillJobId) return;
    let cancelled = false;
    void (async () => {
      try {
        const job = await api.jobs.get(prefillJobId);
        if (cancelled) return;
        setJobPostingId(prefillJobId);
        setTitle(String(job.title || ""));
        setCompany(String(job.company || ""));
        setLocation(job.location != null ? String(job.location) : "");
        setSourceUrl(String(job.source_url || ""));
        setStatus("interested");
      } catch {
        setJobPostingId(prefillJobId);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [prefillJobId]);

  async function createApplication(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.applications.create({
        job_posting_id: jobPostingId.trim() || undefined,
        resume_id: resumeId.trim() || undefined,
        title: title.trim(),
        company: company.trim(),
        location: location.trim() || undefined,
        source_url: sourceUrl.trim(),
        status,
        notes: notes.trim() || undefined,
      });
      setTitle("");
      setCompany("");
      setLocation("");
      setSourceUrl("");
      setJobPostingId("");
      setResumeId("");
      setStatus("interested");
      setNotes("");
      await fetchList();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not create application");
    } finally {
      setSaving(false);
    }
  }

  async function updateStatus(id: string, next: string) {
    try {
      await api.applications.patch(id, { status: next });
      await fetchList();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function removeRow(id: string) {
    if (!confirm("Remove this application from your tracker?")) return;
    try {
      await api.applications.remove(id);
      await fetchList();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Application tracker</h1>
        <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          Log roles you care about, move them through your pipeline, and link them to a resume or an indexed job. From{" "}
          <Link href="/dashboard/search" className="font-medium text-violet-600 hover:underline dark:text-violet-400">
            Search
          </Link>{" "}
          or{" "}
          <Link
            href="/dashboard/recommendations"
            className="font-medium text-violet-600 hover:underline dark:text-violet-400"
          >
            Recommendations
          </Link>
          , use <strong>Track application</strong> to pre-fill a posting.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add application</CardTitle>
          <CardDescription>Required: title, company, posting URL. Optional: resume ID, notes, pipeline status.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={createApplication} className="grid gap-3 md:grid-cols-2">
            <div className="md:col-span-2">
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Posting URL</div>
              <Input
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                placeholder="https://…"
                required
                className="font-mono text-sm"
              />
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Title</div>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} required />
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Company</div>
              <Input value={company} onChange={(e) => setCompany(e.target.value)} required />
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Location</div>
              <Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Optional" />
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Indexed job ID</div>
              <Input
                value={jobPostingId}
                onChange={(e) => setJobPostingId(e.target.value)}
                placeholder="UUID when from job index"
                className="font-mono text-xs"
              />
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Resume ID</div>
              <Input
                value={resumeId}
                onChange={(e) => setResumeId(e.target.value)}
                placeholder="Optional — tie to an uploaded resume"
                className="font-mono text-xs"
              />
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Initial status</div>
              <select
                className="h-10 w-full rounded-md border border-zinc-200 bg-white px-3 text-sm dark:border-zinc-800 dark:bg-zinc-950"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2">
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Notes</div>
              <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="Recruiter name, next step, etc." />
            </div>
            <div className="md:col-span-2 flex flex-wrap gap-3">
              <Button type="submit" disabled={saving}>
                {saving ? "Saving…" : "Add to tracker"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Your applications</CardTitle>
          <CardDescription>Filter by resume or status; update status inline.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Resume ID</div>
              <Input
                value={filterResume}
                onChange={(e) => setFilterResume(e.target.value)}
                placeholder="Filter…"
                className="w-56 font-mono text-xs"
              />
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Status</div>
              <select
                className="h-10 rounded-md border border-zinc-200 bg-white px-3 text-sm dark:border-zinc-800 dark:bg-zinc-950"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <option value="">All</option>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <Button type="button" variant="secondary" onClick={() => void fetchList()} disabled={loading}>
                {loading ? "Loading…" : "Apply filters"}
              </Button>
            </div>
          </div>

          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
              {error}
            </div>
          ) : null}

          {rows.length === 0 && !loading ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">No applications yet. Add one above.</p>
          ) : null}

          <div className="space-y-3">
            {rows.map((a) => (
              <div
                key={a.id}
                className="flex flex-col gap-3 rounded-2xl border border-zinc-200/90 bg-gradient-to-r from-white to-zinc-50/80 p-4 shadow-sm dark:border-zinc-800 dark:from-zinc-950 dark:to-zinc-900/50 sm:flex-row sm:items-start sm:justify-between"
              >
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">{a.title}</h3>
                    <span
                      className={cn(
                        "rounded-full border px-2 py-0.5 text-xs font-semibold capitalize",
                        statusStyle(a.status),
                      )}
                    >
                      {a.status}
                    </span>
                  </div>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    {a.company}
                    {a.location ? ` · ${a.location}` : ""}
                  </p>
                  <a
                    href={a.source_url.startsWith("http") ? a.source_url : `https://${a.source_url}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs font-medium text-violet-600 hover:underline dark:text-violet-400"
                  >
                    Open posting <ExternalLink className="h-3 w-3" />
                  </a>
                  {a.notes ? (
                    <p className="text-xs text-zinc-600 dark:text-zinc-400 line-clamp-2">{a.notes}</p>
                  ) : null}
                  <p className="text-[10px] text-zinc-400 dark:text-zinc-500">
                    Updated {new Date(a.updated_at).toLocaleString()}
                    {a.resume_id ? ` · resume ${a.resume_id}` : ""}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col gap-2 sm:items-end">
                  <select
                    className="h-9 rounded-lg border border-zinc-200 bg-white px-2 text-sm capitalize dark:border-zinc-700 dark:bg-zinc-950"
                    value={a.status}
                    onChange={(e) => void updateStatus(a.id, e.target.value)}
                  >
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40"
                    onClick={() => void removeRow(a.id)}
                  >
                    <Trash2 className="mr-1 h-3.5 w-3.5" />
                    Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function ApplicationsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center gap-2 text-sm text-zinc-500">
          <ClipboardList className="h-4 w-4 animate-pulse" />
          Loading tracker…
        </div>
      }
    >
      <ApplicationsInner />
    </Suspense>
  );
}
