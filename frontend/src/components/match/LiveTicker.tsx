"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { MatchListItem } from "@/lib/types";
import { getLiveMatches } from "@/lib/api";
import ScoreBig from "@/components/ui/ScoreBig";
import LiveBadge from "@/components/ui/LiveBadge";

/** Scrolling live scores bar. Auto-refreshes every 60s (PRD). */
export default function LiveTicker({ initial }: { initial: MatchListItem[] }) {
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
      <div className="card flex items-center gap-3 px-4 py-3 text-sm text-text-secondary">
        <span className="h-2 w-2 rounded-full bg-text-muted" />
        No matches live right now — check today&apos;s fixtures below.
      </div>
    );
  }

  return (
    <div className="card flex items-center gap-3 overflow-hidden p-2 pl-3">
      <LiveBadge />
      <div className="h-5 w-px bg-border" />
      <div className="flex gap-2 overflow-x-auto">
        {matches.map((m) => (
          <Link
            key={m.id}
            href={`/match/${m.id}`}
            className="flex shrink-0 items-center gap-2 whitespace-nowrap rounded-lg bg-surface-raised px-3 py-1.5 text-sm transition-colors hover:text-accent"
          >
            <span className="text-text-secondary">
              {m.home_team.short_name || m.home_team.name}
            </span>
            <ScoreBig home={m.home_score} away={m.away_score} className="text-sm" live />
            <span className="text-text-secondary">
              {m.away_team.short_name || m.away_team.name}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
