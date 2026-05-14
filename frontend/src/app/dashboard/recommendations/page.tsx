"use client";

import { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { JobSearchResultCard, type SearchResultItem } from "@/components/jobs/JobSearchResultCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

function RecommendationsInner() {
  const sp = useSearchParams();
  const presetResumeId = sp.get("resumeId") || "";

  const [resumeId, setResumeId] = useState(presetResumeId);
  const [query, setQuery] = useState("software engineer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResultItem[]>([]);

  const canRun = useMemo(() => query.trim().length > 0 || resumeId.trim().length > 0, [query, resumeId]);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.search({
        mode: "hybrid",
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
        <h1 className="text-2xl font-semibold tracking-tight">Recommendations</h1>
        <p className="mt-1 max-w-3xl text-sm text-zinc-600 dark:text-zinc-400">
          Your <strong className="text-zinc-800 dark:text-zinc-200">personalized feed</strong>: we always rank in{" "}
          <strong className="text-zinc-800 dark:text-zinc-200">hybrid</strong> mode (BM25 + embeddings + resume skill
          overlap + recency). Add a resume ID for explainable match scores; add a query to steer the role.
        </p>
        <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-500">
          Want to compare lexical vs semantic only? Use{" "}
          <Link href="/dashboard/search" className="font-medium text-violet-600 hover:underline dark:text-violet-400">
            Search
          </Link>
          . Topic spikes:{" "}
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
          <CardTitle>Get your ranked list</CardTitle>
          <CardDescription>
            Hybrid mode is fixed here. Provide a resume ID for skill overlap, a query for keywords/semantics, or both.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Resume ID (strongly recommended)</div>
              <Input value={resumeId} onChange={(e) => setResumeId(e.target.value)} placeholder="UUID from upload" />
            </div>
            <div>
              <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Role / query</div>
              <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. backend engineer" />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button onClick={run} disabled={!canRun || loading}>
              {loading ? "Ranking…" : "Get recommendations"}
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setResults([]);
                setError(null);
              }}
              disabled={loading}
            >
              Clear
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
            scoreLayout="grid"
            variant="recommendations"
            trackHref={`/dashboard/applications?job_id=${encodeURIComponent(r.job_id)}`}
          />
        ))}
        {results.length === 0 ? (
          <div className="text-sm text-zinc-600 dark:text-zinc-400">
            No results yet. Ingest jobs (or crawl) and run retrieval.
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function RecommendationsPage() {
  return (
    <Suspense fallback={<div className="text-sm text-zinc-500">Loading…</div>}>
      <RecommendationsInner />
    </Suspense>
  );
}
