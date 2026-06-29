import Link from "next/link";
import type { Metadata } from "next";
import { getArchiveLeagues } from "@/lib/api";
import type { ArchiveLeague } from "@/lib/types";
import {
  COMPETITION_GROUPS,
  competitionGroupOf,
  type CompetitionGroupId,
} from "@/lib/competitions";
import CompetitionBadge from "@/components/ui/CompetitionBadge";

export const revalidate = 600;

export const metadata: Metadata = {
  title: "Archive — Kickstat",
  description:
    "Browse the historical match archive with per-match stats across leagues and seasons.",
};

export default async function HistoryPage() {
  const leagues = await getArchiveLeagues().catch(() => []);
  const total = leagues.reduce((n, l) => n + l.match_count, 0);

  // group archive leagues into competition buckets
  const buckets = new Map<CompetitionGroupId, ArchiveLeague[]>();
  for (const l of leagues) {
    const id = competitionGroupOf(l);
    buckets.set(id, [...(buckets.get(id) ?? []), l]);
  }
  const groups = Array.from(buckets.entries())
    .map(([id, ls]) => ({
      meta: COMPETITION_GROUPS[id],
      leagues: ls.sort((a, b) => b.match_count - a.match_count),
    }))
    .sort((a, b) => a.meta.order - b.meta.order);

  return (
    <div className="space-y-8">
      <header className="relative overflow-hidden rounded-2xl border border-border bg-surface p-6">
        <div className="pointer-events-none absolute inset-0 bg-accent-sheen opacity-60" />
        <div className="relative">
          <span className="stat-label text-accent/90">History</span>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            Match archive
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            {total.toLocaleString()} historical matches with full stats across{" "}
            {leagues.length} competitions.
          </p>
        </div>
      </header>

      {groups.map((g) => (
        <section key={g.meta.id}>
          <div className="mb-3 flex items-baseline gap-2">
            <h2 className="text-sm font-semibold">{g.meta.label}</h2>
            <span className="text-xs text-text-muted">{g.meta.blurb}</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {g.leagues.map((l) => (
              <Link
                key={l.id}
                href={`/history/${l.slug}`}
                className="card card-hover block p-4"
              >
                <div className="flex items-center gap-3">
                  <CompetitionBadge name={l.name} country={l.country} />
                  <div className="min-w-0">
                    <div className="truncate font-medium">{l.name}</div>
                    <div className="truncate text-xs text-text-secondary">
                      {l.country}
                    </div>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between">
                  <span className="stat-label">
                    {l.match_count.toLocaleString()} matches
                  </span>
                  {l.first_year && l.last_year && (
                    <span className="font-mono text-xs text-text-secondary">
                      {l.first_year === l.last_year
                        ? l.first_year
                        : `${l.first_year}–${l.last_year}`}
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
