"use client";

import { useMemo, useState } from "react";
import type { League, Standing } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  groupLeagues,
  seasonsFromStandings,
  standingsForSeason,
  seasonLabel,
} from "@/lib/competitions";
import StandingsTable from "@/components/league/StandingsTable";
import SeasonSelect from "@/components/league/SeasonSelect";
import CompetitionBadge from "@/components/ui/CompetitionBadge";

export interface LeagueStandings {
  league: League;
  standings: Standing[];
}

/** Competition-grouped standings hub with a per-league season switch. */
export default function StandingsBoard({ data }: { data: LeagueStandings[] }) {
  const groups = useMemo(
    () => groupLeagues(data.map((d) => d.league)),
    [data]
  );
  const byId = useMemo(
    () => new Map(data.map((d) => [d.league.id, d])),
    [data]
  );

  const [activeId, setActiveId] = useState(data[0]?.league.id ?? 0);
  const [season, setSeason] = useState<string>(
    () => seasonsFromStandings(data[0]?.standings ?? [])[0] ?? ""
  );

  if (data.length === 0) {
    return (
      <p className="text-sm text-text-secondary">No standings available.</p>
    );
  }

  const current = byId.get(activeId) ?? data[0];
  const seasons = seasonsFromStandings(current.standings);
  const activeSeason = seasons.includes(season) ? season : seasons[0] ?? "";
  const rows = standingsForSeason(current.standings, activeSeason);

  const selectLeague = (id: number) => {
    setActiveId(id);
    const next = byId.get(id);
    setSeason(seasonsFromStandings(next?.standings ?? [])[0] ?? "");
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
      {/* Competition-grouped selector */}
      <aside className="space-y-5 lg:sticky lg:top-20 lg:self-start">
        {groups.map((g) => (
          <div key={g.meta.id}>
            <div className="mb-2 stat-label text-text-muted">{g.meta.label}</div>
            <ul className="space-y-0.5">
              {g.leagues.map((l) => (
                <li key={l.id}>
                  <button
                    type="button"
                    onClick={() => selectLeague(l.id)}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                      l.id === activeId
                        ? "bg-surface-raised text-text-primary"
                        : "text-text-secondary hover:bg-surface-raised/50 hover:text-text-primary"
                    )}
                  >
                    <CompetitionBadge
                      name={l.name}
                      country={l.country}
                      className="h-6 w-6 text-[10px]"
                    />
                    <span className="truncate">{l.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </aside>

      {/* Active league standings */}
      <div className="min-w-0">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">
              {current.league.name}
            </h2>
            <p className="text-xs text-text-secondary">
              {current.league.country}
              {activeSeason && ` · Season ${seasonLabel(activeSeason)}`}
            </p>
          </div>
          <SeasonSelect
            seasons={seasons}
            value={activeSeason}
            onChange={setSeason}
          />
        </div>

        {rows.length > 0 ? (
          <StandingsTable standings={rows} />
        ) : (
          <p className="card p-8 text-center text-sm text-text-secondary">
            No standings for {current.league.name}
            {activeSeason && ` in ${seasonLabel(activeSeason)}`}.
          </p>
        )}

        {/* Zone legend */}
        <div className="mt-3 flex flex-wrap gap-4 text-[11px] text-text-secondary">
          <Legend className="bg-grass-green" label="Top 4" />
          <Legend className="bg-amber-goal" label="Europa places" />
          <Legend className="bg-red-card" label="Relegation" />
        </div>
      </div>
    </div>
  );
}

function Legend({ className, label }: { className: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={cn("h-2 w-2 rounded-full", className)} />
      {label}
    </span>
  );
}
