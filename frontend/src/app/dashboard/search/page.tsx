"use client";

import { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { JobSearchResultCard, type SearchResultItem } from "@/components/jobs/JobSearchResultCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

function SearchInner() {
  const sp = useSearchParams();
  const presetResumeId = sp.get("resumeId") || "";

  const [query, setQuery] = useState("data engineer");
  const [resumeId, setResumeId] = useState(presetResumeId);
  const [mode, setMode] = useState<"lexical" | "semantic" | "hybrid">("hybrid");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResultItem[]>([]);

  const canRun = useMemo(() => query.trim().length > 0 || resumeId.trim().length > 0, [query, resumeId]);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.search({
        mode,
        query: query.trim() || undefined,
        resume_id: resumeId.trim() || undefined,
        k: 20,
      });
      setResults((res.results || []) as SearchResultItem[]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
        <p className="mt-1 max-w-3xl text-sm text-zinc-600 dark:text-zinc-400">
          <strong className="text-zinc-800 dark:text-zinc-200">Explore retrieval</strong>: switch between{" "}
          <strong className="text-zinc-800 dark:text-zinc-200">lexical</strong> (BM25),{" "}
          <strong className="text-zinc-800 dark:text-zinc-200">semantic</strong> (FAISS embeddings), and{" "}
          <strong className="text-zinc-800 dark:text-zinc-200">hybrid</strong> (combined). Optional resume ID still
          feeds skill overlap when you use hybrid.
        </p>
        <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-500">
          For a fixed hybrid &quot;for you&quot; list, use{" "}
          <Link
            href="/dashboard/recommendations"
            className="font-medium text-violet-600 hover:underline dark:text-violet-400"
          >
            Recommendations
          </Link>
          . Topic &amp; anomaly tracking:{" "}
          <Link
            href="/dashboard/insights"
            className="font-medium text-violet-600 hover:underline dark:text-violet-400"
          >
            Topics &amp; events
          </Link>
          .
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Query &amp; mode</CardTitle>
          <CardDescription>
            Lexical ignores vectors; semantic leans on embeddings; hybrid blends both plus skills and recency.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Query</div>
              <Input value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Resume ID (optional)</div>
              <Input value={resumeId} onChange={(e) => setResumeId(e.target.value)} placeholder="UUID" />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Retrieval mode</span>
              <select
                className="h-10 rounded-md border border-zinc-200 bg-white px-3 text-sm dark:border-zinc-800 dark:bg-zinc-950"
                value={mode}
                onChange={(e) => setMode(e.target.value as "lexical" | "semantic" | "hybrid")}
              >
                <option value="hybrid">Hybrid</option>
                <option value="lexical">Lexical (BM25)</option>
                <option value="semantic">Semantic (FAISS)</option>
              </select>
            </div>
            <Button onClick={run} disabled={!canRun || loading}>
              {loading ? "Searching…" : "Search"}
            </Button>
          </div>
          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
              {error}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="space-y-5">
        {results.map((r) => (
          <JobSearchResultCard
            key={r.job_id}
            result={r}
            scoreLayout="inline"
            variant="search"
            trackHref={`/dashboard/applications?job_id=${encodeURIComponent(r.job_id)}`}
          />
        ))}
        {results.length === 0 ? (
          <div className="text-sm text-zinc-600 dark:text-zinc-400">No results yet.</div>
        ) : null}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="text-sm text-zinc-500">Loading…</div>}>
      <SearchInner />
    </Suspense>
  );
}
