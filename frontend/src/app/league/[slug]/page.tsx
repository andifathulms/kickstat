import { notFound } from "next/navigation";
import {
  getLeague,
  getLeagueFixtures,
  getLeagueResults,
  getStandings,
} from "@/lib/api";
import StandingsTable from "@/components/league/StandingsTable";
import MatchList from "@/components/match/MatchList";
import StatLabel from "@/components/ui/StatLabel";

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

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">{league.name}</h1>
        <p className="text-text-secondary text-sm">
          {league.country} · {league.season}
        </p>
      </header>

      <section>
        <StatLabel className="block mb-3">Standings</StatLabel>
        {standings.length > 0 ? (
          <StandingsTable standings={standings} />
        ) : (
          <p className="text-text-secondary text-sm">No standings available.</p>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-4">Upcoming fixtures</h2>
        <MatchList
          matches={fixtures?.results ?? []}
          emptyText="No upcoming fixtures."
        />
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-4">Recent results</h2>
        <MatchList
          matches={results?.results ?? []}
          emptyText="No recent results."
        />
      </section>
    </div>
  );
}
