import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getArchiveLeagues,
  getHistoryMatches,
  getLeague,
  getLeagueFixtures,
  getLeagueResults,
  getStandings,
} from "@/lib/api";
import {
  COMPETITION_GROUPS,
  competitionGroupOf,
  findHistoryLeague,
  leagueSeasonOptions,
  seasonDateRange,
  seasonLabel,
  standingsForSeason,
} from "@/lib/competitions";
import StandingsTable from "@/components/league/StandingsTable";
import SeasonTabs from "@/components/league/SeasonTabs";
import MatchList from "@/components/match/MatchList";
import HistoryMatchRow from "@/components/match/HistoryMatchRow";
import SectionHeader from "@/components/ui/SectionHeader";
import CompetitionBadge from "@/components/ui/CompetitionBadge";

export const revalidate = 60;

const PAGE_SIZE = 20;

export default async function LeaguePage({
  params,
  searchParams,
}: {
  params: { slug: string };
  searchParams: { season?: string; page?: string };
}) {
  let league;
  try {
    league = await getLeague(params.slug);
  } catch {
    notFound();
  }

  const archive = await getArchiveLeagues().catch(() => []);
  const history = findHistoryLeague(league, archive);
  const seasons = leagueSeasonOptions(league.season, history);

  const requested = searchParams.season;
  const selected =
    requested && seasons.some((s) => s.value === requested)
      ? requested
      : league.season;
  const isCurrent = selected === league.season;

  const group = COMPETITION_GROUPS[competitionGroupOf(league)];

  return (
    <div className="space-y-8">
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
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <CompetitionBadge
              name={league.name}
              className="h-12 w-12 text-base"
            />
            <div>
              <span className="stat-label text-accent/90">{group.label}</span>
              <h1 className="text-2xl font-semibold tracking-tight">
                {league.name}
              </h1>
              <p className="text-sm text-text-secondary">
                {league.country} · {seasonLabel(selected)} season
              </p>
            </div>
          </div>
        </div>
        {seasons.length > 1 && (
          <div className="relative mt-5">
            <SeasonTabs
              seasons={seasons}
              active={selected}
              slug={params.slug}
            />
          </div>
        )}
      </header>

      {isCurrent ? (
        <CurrentSeason slug={params.slug} season={league.season} />
      ) : (
        <PastSeason
          history={history}
          season={selected}
          page={Math.max(1, Number(searchParams.page) || 1)}
          slug={params.slug}
        />
      )}
    </div>
  );
}

/* Current season: live standings + fixtures + results */
async function CurrentSeason({
  slug,
  season,
}: {
  slug: string;
  season: string;
}) {
  const [standings, fixtures, results] = await Promise.all([
    getStandings(slug).catch(() => []),
    getLeagueFixtures(slug).catch(() => null),
    getLeagueResults(slug).catch(() => null),
  ]);
  const rows = standingsForSeason(standings, season);

  return (
    <>
      <section>
        <SectionHeader eyebrow="Table" title="Standings" />
        {rows.length > 0 ? (
          <StandingsTable standings={rows} />
        ) : (
          <p className="card p-8 text-center text-sm text-text-secondary">
            No standings available for this season yet.
          </p>
        )}
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
    </>
  );
}

/* Past season: archived matches (with stats) for the selected season */
async function PastSeason({
  history,
  season,
  page,
  slug,
}: {
  history: Awaited<ReturnType<typeof getArchiveLeagues>>[number] | null;
  season: string;
  page: number;
  slug: string;
}) {
  if (!history) {
    return (
      <p className="card p-8 text-center text-sm text-text-secondary">
        No archived data available for past seasons of this competition.
      </p>
    );
  }

  const { dateFrom, dateTo } = seasonDateRange(season);
  const data = await getHistoryMatches({
    league: history.id,
    page,
    dateFrom,
    dateTo,
  }).catch(() => ({ count: 0, next: null, previous: null, results: [] }));

  const totalPages = Math.max(1, Math.ceil(data.count / PAGE_SIZE));

  return (
    <>
      <section>
        <div className="card flex items-center gap-3 p-4 text-sm text-text-secondary">
          <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-surface-raised text-text-primary">
            i
          </span>
          League tables aren&apos;t recorded for archived seasons — showing the{" "}
          <span className="text-text-primary">
            {data.count.toLocaleString()}
          </span>{" "}
          matches from {seasonLabel(season)} with full stats.
        </div>
      </section>

      <section>
        <SectionHeader
          eyebrow="Archive"
          title={`${seasonLabel(season)} matches`}
        />
        {data.results.length === 0 ? (
          <p className="card p-8 text-center text-sm text-text-secondary">
            No matches recorded for this season.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {data.results.map((m) => (
              <HistoryMatchRow key={m.id} match={m} />
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <div className="mt-5 flex items-center justify-between">
            <PageLink
              slug={slug}
              season={season}
              page={page - 1}
              disabled={page <= 1}
            >
              ← Prev
            </PageLink>
            <span className="font-mono text-sm text-text-secondary">
              Page {page} of {totalPages}
            </span>
            <PageLink
              slug={slug}
              season={season}
              page={page + 1}
              disabled={page >= totalPages}
            >
              Next →
            </PageLink>
          </div>
        )}
      </section>
    </>
  );
}

function PageLink({
  slug,
  season,
  page,
  disabled,
  children,
}: {
  slug: string;
  season: string;
  page: number;
  disabled: boolean;
  children: React.ReactNode;
}) {
  if (disabled) {
    return <span className="text-sm text-text-muted">{children}</span>;
  }
  const q = new URLSearchParams({ season });
  if (page > 1) q.set("page", String(page));
  return (
    <Link
      href={`/league/${slug}?${q.toString()}`}
      scroll={false}
      className="text-sm text-text-primary hover:text-accent"
    >
      {children}
    </Link>
  );
}
