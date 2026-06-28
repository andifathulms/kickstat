"use client";

import { useState } from "react";
import type { Standing } from "@/lib/types";
import {
  seasonsFromStandings,
  standingsForSeason,
} from "@/lib/competitions";
import StandingsTable from "@/components/league/StandingsTable";
import SeasonSelect from "@/components/league/SeasonSelect";

/** Standings for a single league with an inline season switcher. */
export default function LeagueStandings({
  standings,
}: {
  standings: Standing[];
}) {
  const seasons = seasonsFromStandings(standings);
  const [season, setSeason] = useState(seasons[0] ?? "");
  const active = seasons.includes(season) ? season : seasons[0] ?? "";
  const rows = standingsForSeason(standings, active);

  if (standings.length === 0) {
    return (
      <p className="card p-8 text-center text-sm text-text-secondary">
        No standings available.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <SeasonSelect seasons={seasons} value={active} onChange={setSeason} />
      </div>
      <StandingsTable standings={rows} />
    </div>
  );
}
