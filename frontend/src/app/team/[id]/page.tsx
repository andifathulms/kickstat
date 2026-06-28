import Link from "next/link";
import { notFound } from "next/navigation";
import { getTeamFixtures, getTeamForm } from "@/lib/api";
import { resultFor } from "@/lib/utils";
import FormBadges from "@/components/team/FormBadge";
import MatchList from "@/components/match/MatchList";
import SectionHeader from "@/components/ui/SectionHeader";
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

  // Team identity from the first match where this team appears.
  const sample = form[0] ?? fixtures[0];
  const isHome = sample?.home_team.id === teamId;
  const team = sample
    ? isHome
      ? sample.home_team
      : sample.away_team
    : null;
  const teamName = team?.name ?? `Team ${teamId}`;

  // Form badges oldest → newest (API returns newest first).
  const formResults = [...form]
    .reverse()
    .map((m) => resultFor(m, teamId))
    .filter((r): r is "W" | "D" | "L" => r !== null);

  return (
    <div className="space-y-10">
      <nav className="flex items-center gap-2 text-xs text-text-secondary">
        <Link href="/" className="hover:text-accent">
          Home
        </Link>
        <span className="text-text-muted">/</span>
        <span className="text-text-primary">{teamName}</span>
      </nav>

      <header className="relative overflow-hidden rounded-2xl border border-border bg-surface p-6">
        <div className="pointer-events-none absolute inset-0 bg-accent-sheen opacity-60" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            {team?.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={team.logo_url}
                alt=""
                className="h-12 w-12 object-contain"
              />
            ) : (
              <span className="h-12 w-12 rounded-full bg-surface-raised" />
            )}
            <h1 className="text-2xl font-semibold tracking-tight">{teamName}</h1>
          </div>
          <div className="text-right">
            <StatLabel className="mb-1.5 block">Last 5</StatLabel>
            <FormBadges form={formResults} />
          </div>
        </div>
      </header>

      <section>
        <SectionHeader eyebrow="Full time" title="Recent results" />
        <MatchList matches={form} grouped={false} emptyText="No recent matches." />
      </section>

      <section>
        <SectionHeader eyebrow="Upcoming" title="Fixtures" />
        <MatchList
          matches={fixtures}
          grouped={false}
          emptyText="No upcoming fixtures."
        />
      </section>
    </div>
  );
}
