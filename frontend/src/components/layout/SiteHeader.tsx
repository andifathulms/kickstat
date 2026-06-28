"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { GroupedLeagues } from "@/lib/competitions";
import { cn } from "@/lib/utils";
import CompetitionBadge from "@/components/ui/CompetitionBadge";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/predictions", label: "Predictions" },
  { href: "/history", label: "Archive" },
];

export default function SiteHeader({ groups }: { groups: GroupedLeagues[] }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // close the mega-menu on route change or outside click
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-pitch-black/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent shadow-glow">
              <span className="h-3 w-3 rounded-full bg-accent-ink" />
            </span>
            <span className="font-mono text-lg font-medium tracking-tight">
              kickstat
            </span>
          </Link>

          <nav className="hidden items-center gap-1 text-sm md:flex">
            <NavLink href="/" active={isActive("/")}>
              Home
            </NavLink>

            {/* Competitions mega-menu */}
            <div className="relative" ref={ref}>
              <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                className={cn(
                  "flex items-center gap-1 rounded-lg px-3 py-1.5 transition-colors",
                  pathname.startsWith("/league") ||
                    pathname.startsWith("/standings")
                    ? "text-text-primary"
                    : "text-text-secondary hover:text-text-primary"
                )}
              >
                Competitions
                <svg
                  className={cn(
                    "h-3.5 w-3.5 transition-transform",
                    open && "rotate-180"
                  )}
                  viewBox="0 0 12 12"
                  fill="none"
                >
                  <path
                    d="M3 4.5 6 7.5 9 4.5"
                    stroke="currentColor"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>

              {open && (
                <div className="absolute left-0 top-full mt-2 w-[34rem] max-w-[calc(100vw-2rem)] animate-fade-up rounded-xl border border-border bg-surface p-4 shadow-panel">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="stat-label">Browse by competition</span>
                    <Link
                      href="/standings"
                      className="text-xs text-accent hover:underline"
                    >
                      All standings →
                    </Link>
                  </div>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {groups.map((g) => (
                      <div key={g.meta.id}>
                        <div className="mb-1.5 stat-label text-text-muted">
                          {g.meta.label}
                        </div>
                        <ul className="space-y-0.5">
                          {g.leagues.map((l) => (
                            <li key={l.id}>
                              <Link
                                href={`/league/${l.slug}`}
                                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-text-secondary transition-colors hover:bg-surface-raised hover:text-text-primary"
                              >
                                <CompetitionBadge
                                  name={l.name}
                                  className="h-6 w-6 text-[10px]"
                                />
                                <span className="truncate">{l.name}</span>
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {LINKS.slice(1).map((l) => (
              <NavLink key={l.href} href={l.href} active={isActive(l.href)}>
                {l.label}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Mobile: condensed links */}
        <nav className="flex items-center gap-3 text-sm text-text-secondary md:hidden">
          <Link href="/standings" className="hover:text-text-primary">
            Leagues
          </Link>
          <Link href="/predictions" className="hover:text-text-primary">
            Picks
          </Link>
          <Link href="/history" className="hover:text-text-primary">
            Archive
          </Link>
        </nav>
      </div>
    </header>
  );
}

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "rounded-lg px-3 py-1.5 transition-colors",
        active
          ? "text-text-primary"
          : "text-text-secondary hover:text-text-primary"
      )}
    >
      {children}
    </Link>
  );
}
