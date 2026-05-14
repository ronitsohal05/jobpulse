"use client";

import Link from "next/link";
import {
  Briefcase,
  Building2,
  Calendar,
  ClipboardList,
  ExternalLink,
  Layers,
  Link2,
  MapPin,
  Sparkles,
  Tag,
  Wallet,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type SearchScoreBreakdown = {
  bm25: number;
  semantic: number;
  skill_overlap: number;
  recency: number;
  final: number;
};

export type SearchMatchExplanation = {
  matched_skills: string[];
  missing_skills: string[];
  top_bm25_terms: string[];
  rationale: string;
};

export type SearchResultItem = {
  job_id: string;
  title: string;
  company: string;
  location?: string | null;
  description: string;
  source_url: string;
  normalized_url?: string;
  source?: string | null;
  date_posted?: string | null;
  crawled_at?: string;
  employment_type?: string | null;
  experience_level?: string | null;
  salary?: string | null;
  required_skills?: string[] | null;
  preferred_skills?: string[] | null;
  category?: string;
  category_confidence?: number | null;
  score: SearchScoreBreakdown;
  explanation: SearchMatchExplanation;
};

/** Ensure external job links work (some sources omit the scheme). */
export function safeJobUrl(url: string | null | undefined): string | null {
  const u = (url || "").trim();
  if (!u) return null;
  if (/^https?:\/\//i.test(u)) return u;
  return `https://${u}`;
}

function displayJobLink(url: string): string {
  try {
    const u = new URL(url);
    const s = `${u.hostname}${u.pathname}${u.search || ""}`;
    return s.length > 100 ? `${s.slice(0, 97)}…` : s;
  } catch {
    return url.length > 100 ? `${url.slice(0, 97)}…` : url;
  }
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return null;
  }
}

function SkillChips({
  label,
  skills,
  variant,
}: {
  label: string;
  skills: string[];
  variant: "required" | "preferred" | "matched" | "missing" | "neutral";
}) {
  if (!skills.length) return null;
  const styles: Record<typeof variant, string> = {
    required:
      "border-violet-200/80 bg-violet-50 text-violet-900 dark:border-violet-800/60 dark:bg-violet-950/50 dark:text-violet-100",
    preferred:
      "border-emerald-200/80 bg-emerald-50 text-emerald-900 dark:border-emerald-800/60 dark:bg-emerald-950/40 dark:text-emerald-100",
    matched:
      "border-green-300/90 bg-green-50 text-green-900 dark:border-green-800/70 dark:bg-green-950/45 dark:text-green-100",
    missing:
      "border-amber-200/90 bg-amber-50/90 text-amber-950 dark:border-amber-800/60 dark:bg-amber-950/35 dark:text-amber-100",
    neutral: "border-zinc-200 bg-zinc-50 text-zinc-800 dark:border-zinc-700 dark:bg-zinc-900/50 dark:text-zinc-200",
  };
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        <Tag className="h-3 w-3" aria-hidden />
        {label}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {skills.map((s) => (
          <span
            key={`${label}-${s}`}
            className={cn(
              "rounded-full border px-2.5 py-0.5 text-xs font-medium shadow-[0_1px_0_rgba(0,0,0,0.04)] dark:shadow-none",
              styles[variant],
            )}
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}

export function JobSearchResultCard({
  result,
  scoreLayout = "grid",
  variant = "search",
  trackHref,
}: {
  result: SearchResultItem;
  scoreLayout?: "grid" | "inline";
  /** Search: show BM25 query-term hints. Recommendations: hides them (same API, different emphasis). */
  variant?: "search" | "recommendations";
  /** When set, show a link to add this job to the application tracker (e.g. `/dashboard/applications?job_id=…`). */
  trackHref?: string;
}) {
  const posted = formatDate(result.date_posted);
  const crawled = formatDate(result.crawled_at);
  const jobHref = safeJobUrl(result.source_url);

  const required = result.required_skills?.filter(Boolean) ?? [];
  const preferred = result.preferred_skills?.filter(Boolean) ?? [];
  const matched = result.explanation?.matched_skills?.filter(Boolean) ?? [];
  const missing = result.explanation?.missing_skills?.filter(Boolean) ?? [];
  const bm25Terms = result.explanation?.top_bm25_terms?.filter(Boolean) ?? [];

  return (
    <article
      className={cn(
        "group relative overflow-hidden rounded-2xl border border-zinc-200/90 bg-gradient-to-br from-white via-zinc-50/40 to-violet-50/50 shadow-sm transition-shadow hover:shadow-md",
        "dark:border-zinc-800 dark:from-zinc-950 dark:via-zinc-950 dark:to-violet-950/25 dark:hover:border-zinc-700",
      )}
    >
      <div
        className="pointer-events-none absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-violet-500 via-fuchsia-500 to-indigo-500 opacity-90"
        aria-hidden
      />
      <div className="relative pl-4 pr-4 pb-4 pt-4 sm:pl-5 sm:pr-5 sm:pt-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1 space-y-2">
            <div>
              {jobHref ? (
                <h3 className="text-lg font-semibold leading-snug tracking-tight sm:text-xl">
                  <a
                    href={jobHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-zinc-900 underline decoration-violet-400/70 decoration-2 underline-offset-2 transition-colors hover:text-violet-700 hover:decoration-violet-600 dark:text-zinc-50 dark:decoration-violet-500/50 dark:hover:text-violet-300 dark:hover:decoration-violet-400"
                  >
                    {result.title}
                    <ExternalLink
                      className="ml-1.5 inline-block h-4 w-4 shrink-0 align-text-bottom opacity-60"
                      aria-hidden
                    />
                  </a>
                </h3>
              ) : (
                <h3 className="text-lg font-semibold leading-snug tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-xl">
                  {result.title}
                </h3>
              )}
              {jobHref ? (
                <div className="mt-2">
                  <a
                    href={jobHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex max-w-full items-start gap-2 rounded-lg border border-violet-200/80 bg-violet-50/50 px-2.5 py-2 text-left text-xs font-medium text-violet-800 transition-colors hover:border-violet-300 hover:bg-violet-100/80 dark:border-violet-800/50 dark:bg-violet-950/30 dark:text-violet-200 dark:hover:border-violet-600 dark:hover:bg-violet-950/50 sm:text-sm"
                  >
                    <Link2 className="mt-0.5 h-3.5 w-3.5 shrink-0 opacity-80" aria-hidden />
                    <span className="min-w-0 break-all font-mono leading-snug">{displayJobLink(jobHref)}</span>
                  </a>
                </div>
              ) : null}
              <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-zinc-600 dark:text-zinc-400">
                <span className="inline-flex items-center gap-1 font-medium text-zinc-800 dark:text-zinc-200">
                  <Building2 className="h-3.5 w-3.5 shrink-0 opacity-70" aria-hidden />
                  {result.company}
                </span>
                {result.location ? (
                  <>
                    <span className="text-zinc-300 dark:text-zinc-600" aria-hidden>
                      ·
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5 shrink-0 opacity-70" aria-hidden />
                      {result.location}
                    </span>
                  </>
                ) : null}
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {result.employment_type ? (
                <span className="inline-flex items-center gap-1 rounded-lg border border-zinc-200/90 bg-white/80 px-2 py-1 text-xs font-medium text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900/60 dark:text-zinc-200">
                  <Briefcase className="h-3 w-3 opacity-70" aria-hidden />
                  {result.employment_type}
                </span>
              ) : null}
              {result.experience_level ? (
                <span className="inline-flex items-center gap-1 rounded-lg border border-zinc-200/90 bg-white/80 px-2 py-1 text-xs font-medium text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900/60 dark:text-zinc-200">
                  <Layers className="h-3 w-3 opacity-70" aria-hidden />
                  {result.experience_level}
                </span>
              ) : null}
              {result.salary ? (
                <span className="inline-flex items-center gap-1 rounded-lg border border-zinc-200/90 bg-white/80 px-2 py-1 text-xs font-medium text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900/60 dark:text-zinc-200">
                  <Wallet className="h-3 w-3 opacity-70" aria-hidden />
                  {result.salary}
                </span>
              ) : null}
              {result.category ? (
                <span className="inline-flex items-center gap-1 rounded-lg border border-violet-200/80 bg-violet-50/90 px-2 py-1 text-xs font-medium text-violet-900 dark:border-violet-800/50 dark:bg-violet-950/40 dark:text-violet-100">
                  <Sparkles className="h-3 w-3 opacity-80" aria-hidden />
                  {result.category.replace(/_/g, " ")}
                  {result.category_confidence != null && result.category_confidence > 0 ? (
                    <span className="opacity-70">· {result.category_confidence}%</span>
                  ) : null}
                </span>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-500 dark:text-zinc-400">
              {posted ? (
                <span className="inline-flex items-center gap-1">
                  <Calendar className="h-3 w-3" aria-hidden />
                  Posted {posted}
                </span>
              ) : null}
              {crawled ? (
                <span className="inline-flex items-center gap-1">
                  <Calendar className="h-3 w-3 opacity-60" aria-hidden />
                  Indexed {crawled}
                </span>
              ) : null}
              {result.source ? (
                <span className="truncate text-zinc-500 dark:text-zinc-500" title={result.source}>
                  Source: {result.source}
                </span>
              ) : null}
            </div>
          </div>

          <div className="flex shrink-0 flex-col gap-2 sm:items-end sm:pt-0.5">
            {trackHref ? (
              <Link
                href={trackHref}
                className={cn(
                  "inline-flex items-center justify-center gap-2 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm font-semibold text-zinc-800 shadow-sm transition-colors",
                  "hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-900",
                  "dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:hover:border-emerald-800 dark:hover:bg-emerald-950/30",
                )}
              >
                <ClipboardList className="h-4 w-4 shrink-0 opacity-80" aria-hidden />
                Track application
              </Link>
            ) : null}
            {jobHref ? (
              <a
                href={jobHref}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                  "inline-flex items-center gap-2 rounded-xl border border-violet-200 bg-white px-3 py-2 text-sm font-semibold text-violet-700 shadow-sm transition-colors",
                  "hover:border-violet-300 hover:bg-violet-50 hover:text-violet-800",
                  "dark:border-violet-800/70 dark:bg-violet-950/40 dark:text-violet-200 dark:hover:bg-violet-950/70",
                )}
              >
                <span className="max-w-[200px] truncate sm:max-w-[240px]">Open posting</span>
                <ExternalLink className="h-4 w-4 shrink-0 opacity-80" aria-hidden />
              </a>
            ) : (
              <span className="text-xs text-zinc-500">No posting URL</span>
            )}
          </div>
        </div>

        {(required.length > 0 || preferred.length > 0) && (
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <SkillChips label="Required skills" skills={required} variant="required" />
            <SkillChips label="Preferred skills" skills={preferred} variant="preferred" />
          </div>
        )}

        {(matched.length > 0 || missing.length > 0) && (
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <SkillChips label="Matched to your resume" skills={matched} variant="matched" />
            <SkillChips label="Gaps vs your resume" skills={missing} variant="missing" />
          </div>
        )}

        {variant === "search" && bm25Terms.length > 0 ? (
          <div className="mt-3 rounded-lg border border-dashed border-zinc-200 bg-zinc-50/80 px-3 py-2 text-xs text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900/30 dark:text-zinc-400">
            <span className="font-semibold text-zinc-700 dark:text-zinc-300">Lexical query terms: </span>
            {bm25Terms.join(" · ")}
          </div>
        ) : null}

        <div className="mt-4 border-t border-zinc-200/80 pt-4 dark:border-zinc-800">
          {scoreLayout === "grid" ? (
            <div className="grid gap-2 sm:grid-cols-5">
              <ScoreCell label="Final" value={`${Math.round((result.score.final || 0) * 100)}%`} emphasis />
              <ScoreCell label="BM25" value={(result.score.bm25 || 0).toFixed(3)} />
              <ScoreCell label="Semantic" value={(result.score.semantic || 0).toFixed(3)} />
              <ScoreCell label="Overlap" value={`${Math.round((result.score.skill_overlap || 0) * 100)}%`} />
              <ScoreCell label="Recency" value={(result.score.recency || 0).toFixed(3)} />
            </div>
          ) : (
            <div className="text-sm text-zinc-700 dark:text-zinc-300">
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                Match {Math.round((result.score.final || 0) * 100)}%
              </span>
              <span className="text-zinc-500 dark:text-zinc-400">
                {" "}
                · BM25 {(result.score.bm25 || 0).toFixed(3)} · semantic {(result.score.semantic || 0).toFixed(3)} ·
                overlap {Math.round((result.score.skill_overlap || 0) * 100)}% · recency{" "}
                {(result.score.recency || 0).toFixed(3)}
              </span>
            </div>
          )}
          {result.explanation?.rationale ? (
            <p className="mt-3 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
              {result.explanation.rationale}
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function ScoreCell({
  label,
  value,
  emphasis,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border px-3 py-2 text-sm",
        emphasis
          ? "border-violet-200/90 bg-violet-50/90 dark:border-violet-800/50 dark:bg-violet-950/40"
          : "border-zinc-200/80 bg-white dark:border-zinc-800 dark:bg-zinc-950/80",
      )}
    >
      <div className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">{label}</div>
      <div
        className={cn(
          "mt-0.5 font-semibold tabular-nums text-zinc-900 dark:text-zinc-100",
          emphasis && "text-lg text-violet-800 dark:text-violet-200",
        )}
      >
        {value}
      </div>
    </div>
  );
}
