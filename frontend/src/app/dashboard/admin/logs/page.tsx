"use client";

import { useEffect, useState } from "react";
import { api, type CrawlStats } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function LogsPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [stats, setStats] = useState<CrawlStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [logRes, statsRes] = await Promise.all([api.crawler.logs(100, 0), api.crawler.stats()]);
      setLogs(logRes);
      setStats(statsRes);
    } catch (e: any) {
      setError(e?.message || "Failed to load logs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Crawl logs</h1>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Pages fetched, jobs extracted, duplicates skipped, and extraction failures. Enabled sources are re-crawled on a
          24-hour schedule when the crawl-scheduler service is running.
        </p>
      </div>

      {stats && !loading ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Sources</CardTitle>
            <CardDescription>Active means the source is enabled for scheduled and on-demand crawls.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-6 text-sm">
            <div>
              <span className="text-zinc-500 dark:text-zinc-400">Active sources</span>
              <div className="text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">{stats.active_sources}</div>
            </div>
            <div>
              <span className="text-zinc-500 dark:text-zinc-400">Total configured</span>
              <div className="text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">{stats.total_sources}</div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
          {error}
        </div>
      ) : null}

      {loading ? <div className="text-sm text-zinc-600 dark:text-zinc-400">Loading…</div> : null}

      <div className="grid gap-4">
        {logs.map((l) => (
          <Card key={l.id}>
            <CardHeader>
              <CardTitle className="truncate">{l.url}</CardTitle>
              <CardDescription>
                {l.status}
                {l.http_status ? ` · HTTP ${l.http_status}` : ""} · {new Date(l.created_at).toLocaleString()}
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-2 text-sm text-zinc-600 dark:text-zinc-400 md:grid-cols-3">
              <div>Pages: {l.pages_fetched}</div>
              <div>Jobs: {l.jobs_extracted}</div>
              <div>Duplicates: {l.duplicates_skipped}</div>
              {l.message ? (
                <div className="md:col-span-3">
                  <span className="font-medium text-zinc-700 dark:text-zinc-200">Message:</span> {l.message}
                </div>
              ) : null}
            </CardContent>
          </Card>
        ))}
        {logs.length === 0 && !loading ? (
          <div className="text-sm text-zinc-600 dark:text-zinc-400">No logs yet.</div>
        ) : null}
      </div>
    </div>
  );
}

