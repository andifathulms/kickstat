import type { Metadata } from "next";
import { getLeagues, getStandings } from "@/lib/api";
import StandingsBoard, {
  type LeagueStandings,
} from "@/components/league/StandingsBoard";

export const revalidate = 120;

export const metadata: Metadata = {
  title: "Competitions — Kickstat",
  description: "League standings by competition and season across all leagues.",
};

export default async function StandingsPage() {
  const leagues = await getLeagues().catch(() => ({
    count: 0,
    next: null,
    previous: null,
    results: [],
  }));
  const active = leagues.results.filter((l) => l.is_active);

  const data: LeagueStandings[] = await Promise.all(
    active.map(async (league) => ({
      league,
      standings: await getStandings(league.slug).catch(() => []),
    }))
  );

  return (
    <div className="space-y-6">
      <header>
        <span className="stat-label text-accent/90">Competitions</span>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">
          Standings
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Pick a competition, switch seasons, and read the table.
        </p>
      </header>
      <StandingsBoard data={data} />
    </div>
  );
}
