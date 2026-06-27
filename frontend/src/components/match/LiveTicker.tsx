"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { MatchListItem } from "@/lib/types";
import { getLiveMatches } from "@/lib/api";
import ScoreBig from "@/components/ui/ScoreBig";
import LiveBadge from "@/components/ui/LiveBadge";

/** Scrolling live scores bar. Auto-refreshes every 60s (PRD). */
export default function LiveTicker({
  initial,
}: {
  initial: MatchListItem[];
}) {
  const [matches, setMatches] = useState(initial);

  useEffect(() => {
    const id = setInterval(async () => {
      try {
        setMatches(await getLiveMatches());
      } catch {
        /* keep last known scores on failure */
      }
    }, 60000);
    return () => clearInterval(id);
  }, []);

  if (matches.length === 0) {
    return (
      <div className="card px-4 py-3 text-sm text-text-secondary">
        No matches live right now.
      </div>
    );
  }

  return (
    <div className="card px-3 py-2 flex items-center gap-3 overflow-x-auto">
      <LiveBadge />
      <div className="flex gap-2">
        {matches.map((m) => (
          <Link
            key={m.id}
            href={`/match/${m.id}`}
            className="flex items-center gap-2 whitespace-nowrap rounded-lg bg-surface-raised px-3 py-1.5 text-sm hover:text-grass-green"
          >
            <span className="text-text-secondary">{m.home_team.short_name || m.home_team.name}</span>
            <ScoreBig home={m.home_score} away={m.away_score} className="text-sm" />
            <span className="text-text-secondary">{m.away_team.short_name || m.away_team.name}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
