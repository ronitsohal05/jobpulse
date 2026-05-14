import Link from "next/link";
import { Activity, ClipboardList, FileUp, Search, Sparkles, Wrench } from "lucide-react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const tiles = [
  {
    href: "/dashboard/upload",
    title: "Resume upload",
    description: "Upload a resume for parsing and matching.",
    icon: FileUp,
  },
  {
    href: "/dashboard/recommendations",
    title: "Recommendations",
    description: "Personalized hybrid feed for your resume and query.",
    icon: Sparkles,
  },
  {
    href: "/dashboard/search",
    title: "Search",
    description: "Compare lexical, semantic, and hybrid retrieval modes.",
    icon: Search,
  },
  {
    href: "/dashboard/applications",
    title: "Applications",
    description: "Track statuses, notes, and follow-ups for roles you care about.",
    icon: ClipboardList,
  },
  {
    href: "/dashboard/insights",
    title: "Topics & events",
    description: "Topic trends over time and anomaly detection on skills.",
    icon: Activity,
  },
  {
    href: "/dashboard/admin/sources",
    title: "Crawler",
    description: "Sources, seed import, and crawl logs.",
    icon: Wrench,
  },
];

export default function DashboardHomePage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Upload a resume, search and rank jobs, track your applications, watch topics and hiring spikes, and manage crawls.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {tiles.map((t) => {
          const Icon = t.icon;
          return (
            <Link key={t.href} href={t.href} className="group block">
              <Card className="h-full transition-colors hover:border-zinc-300 dark:hover:border-zinc-700">
                <CardHeader>
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-2 dark:border-zinc-800 dark:bg-zinc-900">
                      <Icon className="h-5 w-5 text-zinc-700 dark:text-zinc-200" />
                    </div>
                    <div>
                      <CardTitle className="text-base group-hover:underline">{t.title}</CardTitle>
                      <CardDescription className="mt-1">{t.description}</CardDescription>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            </Link>
          );
        })}
      </div>
      <p className="mt-8 text-xs text-zinc-500 dark:text-zinc-500">
        Crawl logs:{" "}
        <Link href="/dashboard/admin/logs" className="underline underline-offset-2 hover:text-zinc-800 dark:hover:text-zinc-300">
          open logs
        </Link>
      </p>
    </div>
  );
}
