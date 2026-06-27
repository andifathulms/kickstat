"use client";

import { useState } from "react";
import type { League, Standing } from "@/lib/types";
import { cn } from "@/lib/utils";
import StandingsTable from "@/components/league/StandingsTable";

export interface LeagueStandings {
  league: League;
  standings: Standing[];
}

/** Tabbed view of multiple leagues' standings (all-leagues snapshot). */
export default function StandingsBoard({ data }: { data: LeagueStandings[] }) {
  const [active, setActive] = useState(data[0]?.league.id ?? 0);

  if (data.length === 0) {
    return <p className="text-text-secondary text-sm">No standings available.</p>;
  }

  const current = data.find((d) => d.league.id === active) ?? data[0];

  return (
    <div>
      <div className="flex gap-1 overflow-x-auto pb-2">
        {data.map(({ league }) => (
          <button
            key={league.id}
            onClick={() => setActive(league.id)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors",
              active === league.id
                ? "bg-surface-raised text-text-primary"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            {league.name}
          </button>
        ))}
      </div>
      <div className="mt-3">
        {current.standings.length > 0 ? (
          <StandingsTable standings={current.standings} />
        ) : (
          <p className="text-text-secondary text-sm">
            No standings for {current.league.name}.
          </p>
        )}
      </div>
    </div>
  );
}
