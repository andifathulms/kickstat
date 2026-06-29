"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { search } from "@/lib/api";
import type { SearchHit, SearchResults } from "@/lib/types";
import Avatar from "@/components/ui/Avatar";

const GROUPS: {
  key: keyof SearchResults["results"];
  label: string;
  href: (h: SearchHit) => string;
  crest?: boolean;
}[] = [
  { key: "players", label: "Players", href: (h) => `/player/${h.id}` },
  { key: "coaches", label: "Managers", href: (h) => `/coach/${h.id}` },
  { key: "teams", label: "Teams", href: (h) => `/team/${h.id}` },
  { key: "leagues", label: "Competitions", href: (h) => `/league/${h.slug}` },
  { key: "referees", label: "Referees", href: (h) => `/referee/${h.id}` },
  { key: "stadiums", label: "Stadiums", href: (h) => `/stadium/${h.id}` },
];

export default function SearchBox() {
  const router = useRouter();
  const pathname = usePathname();
  const [query, setQuery] = useState("");
  const [data, setData] = useState<SearchResults | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const latest = useRef(0);

  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    const id = ++latest.current;
    const t = setTimeout(async () => {
      try {
        const res = await search(q);
        if (latest.current === id) {
          setData(res);
          setOpen(true);
        }
      } catch {
        /* ignore */
      } finally {
        if (latest.current === id) setLoading(false);
      }
    }, 220);
    return () => clearTimeout(t);
  }, [query]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (q.length >= 2) router.push(`/search?q=${encodeURIComponent(q)}`);
  };

  const total = data
    ? Object.values(data.results).reduce((n, a) => n + a.length, 0)
    : 0;

  return (
    <div className="relative" ref={ref}>
      <form onSubmit={submit}>
        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-raised px-3 py-1.5 focus-within:border-border-strong">
          <svg className="h-3.5 w-3.5 text-text-muted" viewBox="0 0 16 16" fill="none">
            <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.5" />
            <path d="M11 11l3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => data && setOpen(true)}
            placeholder="Search players, teams…"
            className="w-44 bg-transparent text-sm text-text-primary placeholder:text-text-muted focus:outline-none"
          />
        </div>
      </form>

      {open && query.trim().length >= 2 && (
        <div className="absolute right-0 top-full mt-2 max-h-[70vh] w-80 overflow-y-auto rounded-xl border border-border bg-surface p-2 shadow-panel">
          {total === 0 ? (
            <p className="px-2 py-3 text-sm text-text-secondary">
              {loading ? "Searching…" : `No results for “${query.trim()}”.`}
            </p>
          ) : (
            <>
              {GROUPS.map(({ key, label, href }) => {
                const hits = data!.results[key].slice(0, 5);
                if (hits.length === 0) return null;
                return (
                  <div key={key} className="mb-1">
                    <div className="px-2 py-1 stat-label text-text-muted">
                      {label}
                    </div>
                    {hits.map((h) => (
                      <Link
                        key={`${key}-${h.id}`}
                        href={href(h)}
                        className="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm hover:bg-surface-raised"
                      >
                        <Avatar name={h.name} className="h-6 w-6 text-[10px]" />
                        <span className="min-w-0">
                          <span className="block truncate">{h.name}</span>
                          {h.detail && (
                            <span className="block truncate text-xs text-text-secondary">
                              {h.detail}
                            </span>
                          )}
                        </span>
                      </Link>
                    ))}
                  </div>
                );
              })}
              <button
                onClick={submit}
                className="mt-1 block w-full rounded-md px-2 py-2 text-left text-xs text-accent hover:bg-surface-raised"
              >
                See all results for “{query.trim()}” →
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
