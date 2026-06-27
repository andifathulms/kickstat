import type { Metadata } from "next";
import { getLeagues, getStandings } from "@/lib/api";
import StandingsBoard, {
  type LeagueStandings,
} from "@/components/league/StandingsBoard";

export const revalidate = 120;

export const metadata: Metadata = {
  title: "Standings — Kickstat",
  description: "League standings at a glance across all covered competitions.",
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
      <h1 className="text-2xl font-semibold">Standings</h1>
      <StandingsBoard data={data} />
    </div>
  );
}
