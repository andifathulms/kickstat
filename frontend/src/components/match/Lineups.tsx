import type { MatchDetail, MatchLineupEntry, TeamMini } from "@/lib/types";

function PlayerRow({ p }: { p: MatchLineupEntry }) {
  const name = p.player_nickname || p.player_name;
  return (
    <li className="flex items-center gap-3 py-1.5 text-sm">
      <span className="w-6 shrink-0 text-center font-mono text-xs text-text-secondary tabular-nums">
        {p.shirt_number ?? "–"}
      </span>
      <span className="min-w-0 flex-1 truncate">{name}</span>
      <span className="flex shrink-0 items-center gap-1.5 text-xs">
        {p.subbed_off_minute != null && (
          <span className="text-red-card" title={`Off ${p.subbed_off_minute}'`}>
            ↓{p.subbed_off_minute}&apos;
          </span>
        )}
        {p.subbed_on_minute != null && (
          <span className="text-grass-green" title={`On ${p.subbed_on_minute}'`}>
            ↑{p.subbed_on_minute}&apos;
          </span>
        )}
      </span>
    </li>
  );
}

function TeamColumn({
  team,
  manager,
  players,
}: {
  team: TeamMini;
  manager: string;
  players: MatchLineupEntry[];
}) {
  const starters = players
    .filter((p) => p.is_starter)
    .sort((a, b) => (a.shirt_number ?? 99) - (b.shirt_number ?? 99));
  const bench = players
    .filter((p) => !p.is_starter)
    .sort((a, b) => (a.shirt_number ?? 99) - (b.shirt_number ?? 99));

  return (
    <div className="card p-4 sm:p-5">
      <div className="mb-3 flex items-center gap-2.5">
        {team.logo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={team.logo_url} alt="" className="h-6 w-6 object-contain" />
        ) : (
          <span className="h-6 w-6 rounded-full bg-surface-raised" />
        )}
        <div className="min-w-0">
          <div className="truncate font-semibold">{team.name}</div>
          {manager && (
            <div className="truncate text-xs text-text-secondary">
              {manager}
            </div>
          )}
        </div>
      </div>

      <ul className="divide-y divide-border/40">
        {starters.map((p) => (
          <PlayerRow key={p.player_id} p={p} />
        ))}
      </ul>

      {bench.length > 0 && (
        <>
          <div className="mt-4 mb-1 stat-label">Substitutes</div>
          <ul className="divide-y divide-border/40 opacity-80">
            {bench.map((p) => (
              <PlayerRow key={p.player_id} p={p} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default function Lineups({ match }: { match: MatchDetail }) {
  if (!match.lineups || match.lineups.length === 0) {
    return (
      <p className="card p-8 text-center text-sm text-text-secondary">
        Lineups are not available for this match.
      </p>
    );
  }
  const home = match.lineups.filter((p) => p.team === match.home_team.id);
  const away = match.lineups.filter((p) => p.team === match.away_team.id);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <TeamColumn
          team={match.home_team}
          manager={match.home_coach?.name ?? ""}
          players={home}
        />
        <TeamColumn
          team={match.away_team}
          manager={match.away_coach?.name ?? ""}
          players={away}
        />
      </div>
      {(match.referee || match.stadium) && (
        <div className="card flex flex-wrap items-center gap-x-6 gap-y-1 p-4 text-sm text-text-secondary">
          {match.stadium && (
            <span>
              <span className="stat-label mr-2">Stadium</span>
              {match.stadium.name}
            </span>
          )}
          {match.referee && (
            <span>
              <span className="stat-label mr-2">Referee</span>
              {match.referee.name}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
