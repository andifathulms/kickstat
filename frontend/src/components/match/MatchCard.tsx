"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { MatchListItem } from "@/lib/types";
import { cn, formatKickoffTime } from "@/lib/utils";
import LiveBadge from "@/components/ui/LiveBadge";
import ScoreBig from "@/components/ui/ScoreBig";
import TeamCard from "@/components/team/TeamCard";

/** Minutes elapsed since kickoff, clamped to 90+ for display. */
function liveMinute(kickoff: string): string {
  const diffMin = Math.floor((Date.now() - new Date(kickoff).getTime()) / 60000);
  if (diffMin < 0) return "0'";
  if (diffMin > 90) return "90+'";
  return `${diffMin}'`;
}

export default function MatchCard({
  match,
  showLeague = false,
}: {
  match: MatchListItem;
  showLeague?: boolean;
}) {
  const isLive = match.status === "LIVE";
  const [minute, setMinute] = useState(() =>
    isLive ? liveMinute(match.kickoff) : ""
  );

  useEffect(() => {
    if (!isLive) return;
    const tick = () => setMinute(liveMinute(match.kickoff));
    tick();
    const id = setInterval(tick, 60000); // client-side increment
    return () => clearInterval(id);
  }, [isLive, match.kickoff]);

  return (
    <Link
      href={`/match/${match.id}`}
      className={cn(
        "card card-hover block p-4",
        isLive && "border-grass-green/40 animate-live-pulse"
      )}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="truncate text-xs text-text-secondary">
          {showLeague
            ? match.league_name
            : match.matchday
              ? `Matchday ${match.matchday}`
              : " "}
        </span>
        {isLive ? (
          <LiveBadge minute={minute} />
        ) : match.status === "FINISHED" ? (
          <span className="chip px-2 py-0.5 text-[10px] font-medium">FT</span>
        ) : (
          <span className="font-mono text-xs text-text-secondary">
            {formatKickoffTime(match.kickoff)}
          </span>
        )}
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <TeamCard team={match.home_team} />
        <div className="px-2 text-center">
          {match.status === "SCHEDULED" ? (
            <span className="font-mono text-sm text-text-muted">vs</span>
          ) : (
            <ScoreBig
              home={match.home_score}
              away={match.away_score}
              className="text-2xl"
              live={isLive}
            />
          )}
        </div>
        <TeamCard team={match.away_team} align="right" />
      </div>
    </Link>
  );
}
