import Link from "next/link";
import type { Metadata } from "next";
import { search } from "@/lib/api";
import type { SearchHit } from "@/lib/types";

export const metadata: Metadata = { title: "Search — Kickstat" };

const GROUPS: {
  key: keyof Awaited<ReturnType<typeof search>>["results"];
  label: string;
  href: (h: SearchHit) => string;
}[] = [
  { key: "players", label: "Players", href: (h) => `/player/${h.id}` },
  { key: "coaches", label: "Managers", href: (h) => `/coach/${h.id}` },
  { key: "teams", label: "Teams", href: (h) => `/team/${h.id}` },
  { key: "leagues", label: "Competitions", href: (h) => `/league/${h.slug}` },
  { key: "referees", label: "Referees", href: (h) => `/referee/${h.id}` },
  { key: "stadiums", label: "Stadiums", href: (h) => `/stadium/${h.id}` },
];

export default async function SearchPage({
  searchParams,
}: {
  searchParams: { q?: string };
}) {
  const q = (searchParams.q ?? "").trim();
  const data =
    q.length >= 2 ? await search(q).catch(() => null) : null;
  const total = data
    ? Object.values(data.results).reduce((n, arr) => n + arr.length, 0)
    : 0;

  return (
    <div className="space-y-8">
      <header>
        <span className="stat-label text-accent/90">Search</span>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">
          Find anything
        </h1>
        <form action="/search" method="get" className="mt-4 max-w-xl">
          <input
            name="q"
            defaultValue={q}
            autoFocus
            placeholder="Search players, managers, teams, referees, stadiums…"
            className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:border-border-strong focus:outline-none"
          />
        </form>
      </header>

      {q.length < 2 ? (
        <p className="text-sm text-text-secondary">
          Type at least 2 characters to search.
        </p>
      ) : total === 0 ? (
        <p className="card p-8 text-center text-sm text-text-secondary">
          No results for &ldquo;{q}&rdquo;.
        </p>
      ) : (
        <div className="space-y-8">
          {GROUPS.map(({ key, label, href }) => {
            const hits = data!.results[key];
            if (hits.length === 0) return null;
            return (
              <section key={key}>
                <div className="mb-3 flex items-baseline gap-2">
                  <h2 className="text-sm font-semibold">{label}</h2>
                  <span className="text-xs text-text-muted">{hits.length}</span>
                </div>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {hits.map((h) => (
                    <Link
                      key={`${key}-${h.id}`}
                      href={href(h)}
                      className="card card-hover flex items-center justify-between gap-3 p-3"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium">
                          {h.name}
                        </span>
                        {h.detail && (
                          <span className="block truncate text-xs text-text-secondary">
                            {h.detail}
                          </span>
                        )}
                      </span>
                      <span className="text-text-muted">→</span>
                    </Link>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
