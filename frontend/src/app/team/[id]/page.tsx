import { notFound } from "next/navigation";
import { getTeamFixtures, getTeamForm } from "@/lib/api";
import { resultFor } from "@/lib/utils";
import FormBadges from "@/components/team/FormBadge";
import MatchList from "@/components/match/MatchList";
import StatLabel from "@/components/ui/StatLabel";

export const revalidate = 60;

export default async function TeamPage({
  params,
}: {
  params: { id: string };
}) {
  const teamId = Number(params.id);
  let form;
  try {
    form = await getTeamForm(teamId);
  } catch {
    notFound();
  }
  const fixtures = await getTeamFixtures(teamId).catch(() => []);

  // Team name comes from the first match where this team appears.
  const sample = form[0] ?? fixtures[0];
  const teamName =
    sample?.home_team.id === teamId
      ? sample?.home_team.name
      : sample?.away_team.name ?? `Team ${teamId}`;

  // Form badges oldest → newest (API returns newest first).
  const formResults = [...form]
    .reverse()
    .map((m) => resultFor(m, teamId))
    .filter((r): r is "W" | "D" | "L" => r !== null);

  return (
    <div className="space-y-8">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{teamName}</h1>
        <div>
          <StatLabel className="block mb-1 text-right">Last 5</StatLabel>
          <FormBadges form={formResults} />
        </div>
      </header>

      <section>
        <h2 className="text-lg font-semibold mb-4">Recent results</h2>
        <MatchList matches={form} emptyText="No recent matches." />
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-4">Upcoming fixtures</h2>
        <MatchList matches={fixtures} emptyText="No upcoming fixtures." />
      </section>
    </div>
  );
}
