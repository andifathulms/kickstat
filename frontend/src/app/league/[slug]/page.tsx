import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getArchiveLeagues,
  getHistoryMatches,
  getLeague,
  getLeagueFixtures,
  getLeagueResults,
  getLeagueSeasons,
  getStandings,
} from "@/lib/api";
import {
  COMPETITION_GROUPS,
  competitionGroupOf,
  findHistoryLeague,
  buildSeasonOptions,
  seasonDateRange,
  seasonLabel,
  type SeasonOption,
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

  const [activeSeasons, historySeasons] = await Promise.all([
    getLeagueSeasons(league.id).catch(() => []),
    history ? getLeagueSeasons(history.id).catch(() => []) : Promise.resolve([]),
  ]);

  const seasons = buildSeasonOptions(
    league,
    activeSeasons,
    history,
    historySeasons
  );

  const requested = searchParams.season;
  const selected =
    seasons.find((s) => s.value === requested) ?? seasons[0] ?? null;

  const group = COMPETITION_GROUPS[competitionGroupOf(league)];
  const page = Math.max(1, Number(searchParams.page) || 1);

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
        <div className="relative flex flex-wrap items-center gap-4">
          <CompetitionBadge name={league.name} className="h-12 w-12 text-base" />
          <div>
            <span className="stat-label text-accent/90">{group.label}</span>
            <h1 className="text-2xl font-semibold tracking-tight">
              {league.name}
            </h1>
            <p className="text-sm text-text-secondary">
              {league.country}
              {selected && ` · ${seasonLabel(selected.value)} season`}
              {selected && !selected.isLive && (
                <span className="ml-1 text-text-muted">(archived)</span>
              )}
            </p>
          </div>
        </div>
        {seasons.length > 1 && selected && (
          <div className="relative mt-5">
            <SeasonTabs
              seasons={seasons}
              active={selected.value}
              slug={params.slug}
            />
          </div>
        )}
      </header>

      {!selected ? (
        <p className="card p-8 text-center text-sm text-text-secondary">
          No match data is available for this competition yet.
        </p>
      ) : selected.isLive ? (
        <LiveSeason slug={params.slug} season={selected} />
      ) : (
        <ArchivedSeason
          season={selected}
          page={page}
          slug={params.slug}
        />
      )}
    </div>
  );
}

/* Live season: stored standings + upcoming fixtures + recent results */
async function LiveSeason({
  slug,
  season,
}: {
  slug: string;
  season: SeasonOption;
}) {
  const [standings, fixtures, results] = await Promise.all([
    getStandings(season.leagueId, season.value).catch(() => []),
    getLeagueFixtures(slug).catch(() => null),
    getLeagueResults(slug).catch(() => null),
  ]);

  return (
    <>
      <StandingsSection standings={standings} season={season} />

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

/* Archived season: computed standings + that season's matches (with stats) */
async function ArchivedSeason({
  season,
  page,
  slug,
}: {
  season: SeasonOption;
  page: number;
  slug: string;
}) {
  const { dateFrom, dateTo } = seasonDateRange(season.value);
  const [standings, data] = await Promise.all([
    getStandings(season.leagueId, season.value).catch(() => []),
    getHistoryMatches({
      league: season.leagueId,
      page,
      dateFrom,
      dateTo,
    }).catch(() => ({ count: 0, next: null, previous: null, results: [] })),
  ]);

  const totalPages = Math.max(1, Math.ceil(data.count / PAGE_SIZE));

  return (
    <>
      <StandingsSection standings={standings} season={season} />

      <section>
        <SectionHeader
          eyebrow="Archive"
          title={`${seasonLabel(season.value)} matches`}
        >
          <span className="chip">
            <span className="font-mono text-text-primary">
              {data.count.toLocaleString()}
            </span>
            played
          </span>
        </SectionHeader>

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
              season={season.value}
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
              season={season.value}
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

function StandingsSection({
  standings,
  season,
}: {
  standings: Awaited<ReturnType<typeof getStandings>>;
  season: SeasonOption;
}) {
  return (
    <section>
      <SectionHeader eyebrow="Table" title="Standings">
        {standings.length > 0 && !season.isLive && (
          <span className="chip">computed from results</span>
        )}
      </SectionHeader>
      {standings.length > 0 ? (
        <StandingsTable standings={standings} />
      ) : (
        <p className="card p-8 text-center text-sm text-text-secondary">
          No standings available for this season.
        </p>
      )}
    </section>
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
