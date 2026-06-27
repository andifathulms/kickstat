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

export default function MatchCard({ match }: { match: MatchListItem }) {
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
        "card p-4 block hover:border-text-secondary/40 transition-colors",
        isLive && "border-grass-green/40 animate-live-pulse"
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-text-secondary truncate">
          {match.league_name}
        </span>
        {isLive ? (
          <LiveBadge />
        ) : match.status === "FINISHED" ? (
          <span className="text-xs text-text-secondary">FT</span>
        ) : (
          <span className="text-xs text-text-secondary">
            {formatKickoffTime(match.kickoff)}
          </span>
        )}
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <TeamCard team={match.home_team} />
        <div className="text-center">
          {match.status === "SCHEDULED" ? (
            <span className="font-mono text-text-secondary text-sm">vs</span>
          ) : (
            <ScoreBig
              home={match.home_score}
              away={match.away_score}
              className="text-xl"
            />
          )}
          {isLive && (
            <div className="text-[11px] text-grass-green font-mono mt-0.5">
              {minute}
            </div>
          )}
        </div>
        <TeamCard team={match.away_team} align="right" />
      </div>
    </Link>
  );
}
