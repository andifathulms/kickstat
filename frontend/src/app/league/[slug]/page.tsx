import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getLeague,
  getLeagueFixtures,
  getLeagueResults,
  getStandings,
} from "@/lib/api";
import {
  COMPETITION_GROUPS,
  competitionGroupOf,
  seasonLabel,
} from "@/lib/competitions";
import LeagueStandings from "@/components/league/LeagueStandings";
import MatchList from "@/components/match/MatchList";
import SectionHeader from "@/components/ui/SectionHeader";
import CompetitionBadge from "@/components/ui/CompetitionBadge";

export const revalidate = 60;

export default async function LeaguePage({
  params,
}: {
  params: { slug: string };
}) {
  let league;
  try {
    league = await getLeague(params.slug);
  } catch {
    notFound();
  }

  const [standings, fixtures, results] = await Promise.all([
    getStandings(params.slug).catch(() => []),
    getLeagueFixtures(params.slug).catch(() => null),
    getLeagueResults(params.slug).catch(() => null),
  ]);

  const group = COMPETITION_GROUPS[competitionGroupOf(league)];

  return (
    <div className="space-y-10">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-xs text-text-secondary">
        <Link href="/" className="hover:text-accent">
          Home
        </Link>
        <span className="text-text-muted">/</span>
        <Link href="/standings" className="hover:text-accent">
          Competitions
        </Link>
        <span className="text-text-muted">/</span>
        <span className="text-text-primary">{league.name}</span>
      </nav>

      {/* Header */}
      <header className="relative overflow-hidden rounded-2xl border border-border bg-surface p-6">
        <div className="pointer-events-none absolute inset-0 bg-accent-sheen opacity-60" />
        <div className="relative flex items-center gap-4">
          <CompetitionBadge name={league.name} className="h-12 w-12 text-base" />
          <div>
            <span className="stat-label text-accent/90">{group.label}</span>
            <h1 className="text-2xl font-semibold tracking-tight">
              {league.name}
            </h1>
            <p className="text-sm text-text-secondary">
              {league.country}
              {league.season && ` · ${seasonLabel(league.season)} season`}
            </p>
          </div>
        </div>
      </header>

      <section>
        <SectionHeader eyebrow="Table" title="Standings" />
        <LeagueStandings standings={standings} />
      </section>

      <section>
        <SectionHeader eyebrow="Upcoming" title="Fixtures" />
        <MatchList
          matches={fixtures?.results ?? []}
          grouped={false}
          emptyText="No upcoming fixtures."
        />
      </section>

      <section>
        <SectionHeader eyebrow="Full time" title="Recent results" />
        <MatchList
          matches={results?.results ?? []}
          grouped={false}
          emptyText="No recent results."
        />
      </section>
    </div>
  );
}
