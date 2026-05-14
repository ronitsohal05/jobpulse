"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, BellRing, LineChart as LineChartIcon, RefreshCw } from "lucide-react";
import { api, type EventOut, type TopicWithTrend } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CartesianGrid,
  Line,
  LineChart as ReLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function TopicTrendChart({ topic }: { topic: TopicWithTrend }) {
  const data = (topic.trend || []).map((p) => ({
    label: new Date(p.bucket_start).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    count: p.count,
  }));
  if (data.length === 0) {
    return (
      <p className="text-xs text-zinc-500 dark:text-zinc-400">No weekly buckets yet. Recompute after ingesting jobs.</p>
    );
  }
  return (
    <div className="h-[180px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ReLineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-zinc-200 dark:stroke-zinc-800" />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} className="text-zinc-500" />
          <YAxis width={32} tick={{ fontSize: 10 }} allowDecimals={false} />
          <Tooltip
            contentStyle={{
              borderRadius: "8px",
              border: "1px solid rgb(228 228 231)",
              fontSize: "12px",
            }}
          />
          <Line type="monotone" dataKey="count" stroke="#7c3aed" strokeWidth={2} dot={{ r: 3 }} name="Job count" />
        </ReLineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function InsightsPage() {
  const [topics, setTopics] = useState<TopicWithTrend[]>([]);
  const [events, setEvents] = useState<EventOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"topics" | "events" | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void (async () => {
      setLoading(true);
      setError(null);
      try {
        const [t, e] = await Promise.all([api.topics.list(), api.events.list(80)]);
        if (!alive) return;
        setTopics(t);
        setEvents(e);
      } catch (err: unknown) {
        if (!alive) return;
        setError(err instanceof Error ? err.message : "Failed to load insights");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function runTopics() {
    setBusy("topics");
    setToast(null);
    try {
      const r = await api.topics.recompute();
      setToast(`Topics recomputed: ${JSON.stringify(r)}`);
      const [t, e] = await Promise.all([api.topics.list(), api.events.list(80)]);
      setTopics(t);
      setEvents(e);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Topic recompute failed");
    } finally {
      setBusy(null);
    }
  }

  async function runEvents() {
    setBusy("events");
    setToast(null);
    try {
      const r = await api.events.recompute();
      setToast(`Events recomputed: ${JSON.stringify(r)}`);
      const [t, e] = await Promise.all([api.topics.list(), api.events.list(80)]);
      setTopics(t);
      setEvents(e);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Event recompute failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Topics &amp; event detection</h1>
        <p className="mt-1 max-w-3xl text-sm text-zinc-600 dark:text-zinc-400">
          <strong className="text-zinc-800 dark:text-zinc-200">Topic tracking</strong> clusters skills from postings
          (required + preferred fields, NMF over TF‑IDF) and plots weekly volume. Only jobs with at least one skill are
          labeled. <strong className="text-zinc-800 dark:text-zinc-200">Event detection</strong> flags skills whose
          weekly counts jump versus recent history (z‑score). Recompute after crawling or ingesting new jobs.
        </p>
        <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-500">
          Related:{" "}
          <Link href="/dashboard/search" className="font-medium text-violet-600 hover:underline dark:text-violet-400">
            Search
          </Link>{" "}
          ·{" "}
          <Link
            href="/dashboard/recommendations"
            className="font-medium text-violet-600 hover:underline dark:text-violet-400"
          >
            Recommendations
          </Link>
        </p>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200">
          {error}
        </div>
      ) : null}
      {toast ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2 text-xs text-emerald-900 dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-100">
          {toast}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <Button onClick={() => void runTopics()} disabled={!!busy || loading} variant="default">
          {busy === "topics" ? (
            <>
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              Recomputing topics…
            </>
          ) : (
            <>
              <LineChartIcon className="mr-2 h-4 w-4" />
              Recompute topics
            </>
          )}
        </Button>
        <Button onClick={() => void runEvents()} disabled={!!busy || loading} variant="outline">
          {busy === "events" ? (
            <>
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              Recomputing events…
            </>
          ) : (
            <>
              <BellRing className="mr-2 h-4 w-4" />
              Recompute events
            </>
          )}
        </Button>
        <Button
          variant="ghost"
          disabled={loading || !!busy}
          onClick={() => {
            void (async () => {
              setLoading(true);
              setError(null);
              try {
                const [t, e] = await Promise.all([api.topics.list(), api.events.list(80)]);
                setTopics(t);
                setEvents(e);
              } catch (err: unknown) {
                setError(err instanceof Error ? err.message : "Failed to load insights");
              } finally {
                setLoading(false);
              }
            })();
          }}
        >
          Refresh data
        </Button>
      </div>

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-violet-600 dark:text-violet-400" />
          <h2 className="text-lg font-semibold tracking-tight">Topic trends</h2>
        </div>
        {loading ? (
          <p className="text-sm text-zinc-500">Loading topics…</p>
        ) : topics.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-zinc-600 dark:text-zinc-400">
              No topics yet. Ingest jobs, then run <strong>Recompute topics</strong>.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {topics.map((row) => (
              <Card
                key={row.topic.id}
                className="overflow-hidden border-zinc-200/90 shadow-sm dark:border-zinc-800 dark:bg-zinc-950"
              >
                <CardHeader className="border-b border-zinc-100 bg-gradient-to-r from-violet-50/80 to-transparent pb-3 dark:border-zinc-800 dark:from-violet-950/40">
                  <CardTitle className="text-base">{row.topic.name}</CardTitle>
                  <CardDescription className="line-clamp-2">
                    {row.topic.method} · {(row.topic.keywords || []).slice(0, 8).join(", ")}
                    {(row.topic.keywords?.length || 0) > 8 ? "…" : ""}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-4">
                  <TopicTrendChart topic={row} />
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <BellRing className="h-5 w-5 text-amber-600 dark:text-amber-400" />
          <h2 className="text-lg font-semibold tracking-tight">New events (anomaly detection)</h2>
        </div>
        {loading ? (
          <p className="text-sm text-zinc-500">Loading events…</p>
        ) : events.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-zinc-600 dark:text-zinc-400">
              No anomalies detected yet. Run <strong>Recompute events</strong> after you have several weeks of skill
              counts.
            </CardContent>
          </Card>
        ) : (
          <Card className="overflow-hidden border-zinc-200/90 dark:border-zinc-800">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="border-b border-zinc-200 bg-zinc-50 text-xs font-semibold uppercase tracking-wide text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900/80 dark:text-zinc-400">
                  <tr>
                    <th className="px-4 py-3">Entity</th>
                    <th className="px-4 py-3">Value</th>
                    <th className="px-4 py-3">Z‑score</th>
                    <th className="px-4 py-3">Detected</th>
                    <th className="px-4 py-3">Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                  {events.map((ev) => (
                    <tr key={ev.id} className="bg-white hover:bg-zinc-50/80 dark:bg-zinc-950 dark:hover:bg-zinc-900/50">
                      <td className="px-4 py-3 font-medium text-zinc-900 dark:text-zinc-100">{ev.entity_type}</td>
                      <td className="px-4 py-3 text-violet-700 dark:text-violet-300">{ev.entity_value}</td>
                      <td className="px-4 py-3 tabular-nums font-semibold text-amber-800 dark:text-amber-200">
                        {ev.z_score.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-xs text-zinc-600 dark:text-zinc-400">
                        {new Date(ev.detected_at).toLocaleString()}
                      </td>
                      <td className="max-w-md px-4 py-3 text-xs text-zinc-600 dark:text-zinc-400">{ev.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </section>
    </div>
  );
}
