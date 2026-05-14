"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function SourcesPage() {
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [allowedDomain, setAllowedDomain] = useState("");
  const [pattern, setPattern] = useState("/jobs/");
  const [maxPages, setMaxPages] = useState(50);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.crawler.sources();
      setSources(res);
    } catch (e: any) {
      setError(e?.message || "Failed to load sources");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function create() {
    setError(null);
    try {
      await api.crawler.createSource({
        name,
        base_url: baseUrl,
        allowed_domain: allowedDomain,
        job_link_pattern: pattern,
        max_pages: maxPages,
        crawl_frequency: "daily",
        enabled: true,
      });
      setName("");
      setBaseUrl("");
      setAllowedDomain("");
      await load();
    } catch (e: any) {
      setError(e?.message || "Failed to create source");
    }
  }

  async function run(id: string) {
    setError(null);
    try {
      const res = (await api.crawler.run(id)) as {
        status?: string;
        pages_fetched?: number;
        jobs_extracted?: number;
        duplicates_skipped?: number;
      };
      await load();
      if (res?.status === "disabled") {
        alert("This source is disabled. Turn it on with the Enabled toggle, then run again.");
      } else {
        alert(
          `Crawl finished: status=${res?.status}, pages=${res?.pages_fetched}, jobs=${res?.jobs_extracted}, duplicates skipped=${res?.duplicates_skipped}`,
        );
      }
    } catch (e: any) {
      setError(e?.message || "Crawl failed");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Crawler sources</h1>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
            Editing <span className="font-mono text-xs">infra/crawler_sources.json</span> alone does not load sources — they must exist in the database. Use{" "}
            <strong>Import seed JSON</strong> once, then enable a source. New and re-enabled sources are queued for a crawl automatically; with Docker Compose, the{" "}
            <span className="font-mono text-xs">crawl-scheduler</span> service re-queues every enabled source every 24 hours (override with{" "}
            <span className="font-mono text-xs">CRAWL_SCHEDULE_INTERVAL_S</span>).
          </p>
        </div>
        <Button
          type="button"
          variant="secondary"
          onClick={async () => {
            setError(null);
            try {
              const res = (await api.crawler.seed()) as {
                error?: string;
                seed_file?: string;
                created?: number;
                updated?: number;
              };
              if (res.error) {
                setError(res.error);
              } else {
                await load();
                setError(null);
                alert(
                  `Imported from ${res.seed_file || "seed file"}: ${res.created} created, ${res.updated} updated.`,
                );
              }
            } catch (e: any) {
              setError(e?.message || "Seed failed");
            }
          }}
        >
          Import seed JSON
        </Button>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
          {error}
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Add source</CardTitle>
          <CardDescription>For best results, set a link pattern like `/jobs/`. Listing discovery follows rel=next and common “next” links across multiple search pages (capped from Max pages).</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <div>
            <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Name</div>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="AcmeCareers" />
          </div>
          <div>
            <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Base URL</div>
            <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://example.com/careers" />
          </div>
          <div>
            <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Allowed domain</div>
            <Input value={allowedDomain} onChange={(e) => setAllowedDomain(e.target.value)} placeholder="example.com" />
          </div>
          <div>
            <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Job link pattern</div>
            <Input value={pattern} onChange={(e) => setPattern(e.target.value)} placeholder="/jobs/" />
          </div>
          <div>
            <div className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Max pages</div>
            <Input
              value={String(maxPages)}
              onChange={(e) => setMaxPages(Number(e.target.value || 0))}
              type="number"
              min={1}
              max={1000}
            />
          </div>
          <div className="flex items-end">
            <Button onClick={create} disabled={!name || !baseUrl || !allowedDomain}>
              Create source
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {loading ? <div className="text-sm text-zinc-600 dark:text-zinc-400">Loading…</div> : null}
        {sources.map((s) => (
          <Card key={s.id}>
            <CardHeader>
              <CardTitle>{s.name}</CardTitle>
              <CardDescription>
                {s.base_url} · allowed `{s.allowed_domain}` · max {s.max_pages}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-sm text-zinc-600 dark:text-zinc-400">
                Pattern: <span className="font-mono text-xs">{s.job_link_pattern || "(none)"}</span>
                <span className="mx-2">·</span>
                <label className="inline-flex cursor-pointer items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!!s.enabled}
                    onChange={async (e) => {
                      try {
                        await api.crawler.patchSource(s.id, { enabled: e.target.checked });
                        await load();
                      } catch (err: any) {
                        setError(err?.message || "Update failed");
                      }
                    }}
                    className="rounded border-zinc-300"
                  />
                  <span>Enabled</span>
                </label>
              </div>
              <Button variant="outline" onClick={() => run(s.id)}>
                Run crawl
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

