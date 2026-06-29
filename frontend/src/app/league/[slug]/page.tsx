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
  findStatsBombLeagues,
  mergeSeasonSources,
  normalizeVenue,
  seasonDateRange,
  seasonLabel,
  type SeasonOption,
  type SeasonSource,
  type Venue,
} from "@/lib/competitions";
import StandingsTable from "@/components/league/StandingsTable";
import SeasonTabs from "@/components/league/SeasonTabs";
import VenueTabs from "@/components/league/VenueTabs";
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
  searchParams: { season?: string; page?: string; venue?: string };
}) {
  let league;
  try {
    league = await getLeague(params.slug);
  } catch {
    notFound();
  }

  const archive = await getArchiveLeagues().catch(() => []);
  const history = findHistoryLeague(league, archive);
  const statsbomb = findStatsBombLeagues(league, archive);

  // Seasons from every source: the live row, each StatsBomb season row (rich
  // data), and the football-data history row.
  const sourceLeagues = [
    { kind: "live" as const, id: league.id },
    ...statsbomb.map((sb) => ({ kind: "statsbomb" as const, id: sb.id })),
    ...(history ? [{ kind: "history" as const, id: history.id }] : []),
  ];
  const seasonLists = await Promise.all(
    sourceLeagues.map((s) => getLeagueSeasons(s.id).catch(() => []))
  );
  const sources: SeasonSource[] = sourceLeagues.map((s, i) => ({
    leagueId: s.id,
    kind: s.kind,
    seasons: seasonLists[i],
  }));
  const seasons = mergeSeasonSources(sources);

  const requested = searchParams.season;
  const selected =
    seasons.find((s) => s.value === requested) ?? seasons[0] ?? null;

  const group = COMPETITION_GROUPS[competitionGroupOf(league)];
  const page = Math.max(1, Number(searchParams.page) || 1);
  const venue = normalizeVenue(searchParams.venue);

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
            <p className="flex flex-wrap items-center gap-x-1.5 text-sm text-text-secondary">
              <span>
                {league.country}
                {selected && ` · ${seasonLabel(selected.value)} season`}
              </span>
              {selected && !selected.isLive && (
                <span className="text-text-muted">(archived)</span>
              )}
              {selected?.rich && (
                <span className="rounded-full bg-accent/15 px-2 py-0.5 text-[11px] font-medium text-accent">
                  ✦ Full data — lineups, goals &amp; assists, detailed stats
                </span>
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
        <LiveSeason slug={params.slug} season={selected} venue={venue} />
      ) : (
        <ArchivedSeason
          season={selected}
          page={page}
          slug={params.slug}
          venue={venue}
        />
      )}
    </div>
  );
}

/* Live season: stored standings + upcoming fixtures + recent results */
async function LiveSeason({
  slug,
  season,
  venue,
}: {
  slug: string;
  season: SeasonOption;
  venue: Venue;
}) {
  const [standings, fixtures, results] = await Promise.all([
    getStandings(season.leagueId, season.value, venue).catch(() => []),
    getLeagueFixtures(slug).catch(() => null),
    getLeagueResults(slug).catch(() => null),
  ]);

  return (
    <>
      <StandingsSection
        standings={standings}
        season={season}
        venue={venue}
        slug={slug}
      />

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
  venue,
}: {
  season: SeasonOption;
  page: number;
  slug: string;
  venue: Venue;
}) {
  const { dateFrom, dateTo } = seasonDateRange(season.value);
  const [standings, data] = await Promise.all([
    getStandings(season.leagueId, season.value, venue).catch(() => []),
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
      <StandingsSection
        standings={standings}
        season={season}
        venue={venue}
        slug={slug}
      />

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
  venue,
  slug,
}: {
  standings: Awaited<ReturnType<typeof getStandings>>;
  season: SeasonOption;
  venue: Venue;
  slug: string;
}) {
  return (
    <section>
      <SectionHeader eyebrow="Table" title="Standings">
        <VenueTabs active={venue} slug={slug} season={season.value} />
      </SectionHeader>
      {standings.length > 0 ? (
        <>
          <StandingsTable standings={standings} showZones={venue === "overall"} />
          {(venue !== "overall" || standings[0]?.computed) && (
            <p className="mt-2 text-xs text-text-muted">
              {venue === "overall"
                ? "Table computed from match results."
                : `${venue === "home" ? "Home" : "Away"} record only — each team's ${venue} matches this season.`}
            </p>
          )}
        </>
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
