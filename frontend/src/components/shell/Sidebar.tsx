import Link from "next/link";
import { Activity, Briefcase, ClipboardList, FileUp, LayoutDashboard, Search, Sparkles, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard },
  { href: "/dashboard/upload", label: "Resume upload", icon: FileUp },
  { href: "/dashboard/recommendations", label: "Recommendations", icon: Sparkles },
  { href: "/dashboard/search", label: "Search", icon: Search },
  { href: "/dashboard/applications", label: "Applications", icon: ClipboardList },
  { href: "/dashboard/insights", label: "Topics & events", icon: Activity },
  { href: "/dashboard/admin/sources", label: "Crawler sources", icon: Wrench },
  { href: "/dashboard/admin/logs", label: "Crawl logs", icon: Briefcase },
];

export function Sidebar({ pathname }: { pathname: string }) {
  return (
    <aside className="w-72 shrink-0 border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <nav className="px-3 pb-6 pt-5">
        {nav.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50"
                  : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-50",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
