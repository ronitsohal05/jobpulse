"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/shell/Sidebar";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen bg-zinc-50 text-zinc-900 dark:bg-black dark:text-zinc-50">
      <Sidebar pathname={pathname} />
      <main className="flex-1">
        <div className="mx-auto w-full max-w-6xl px-6 py-8">{children}</div>
      </main>
    </div>
  );
}

