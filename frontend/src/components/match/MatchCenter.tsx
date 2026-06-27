"use client";

import { useState } from "react";
import type { MatchDetail } from "@/lib/types";
import { cn, formatKickoffDate, formatKickoffTime } from "@/lib/utils";
import LiveBadge from "@/components/ui/LiveBadge";
import ScoreBig from "@/components/ui/ScoreBig";
import StatLabel from "@/components/ui/StatLabel";
import StatBar from "@/components/match/StatBar";
import PredictionDonut from "@/components/match/PredictionDonut";
import TeamCard from "@/components/team/TeamCard";

const TABS = ["Overview", "Stats", "Prediction", "Lineups"] as const;
type Tab = (typeof TABS)[number];

export default function MatchCenter({ match }: { match: MatchDetail }) {
  const [tab, setTab] = useState<Tab>("Overview");
  const isLive = match.status === "LIVE";

  return (
    <div className="space-y-5">
      {/* Header */}
      <div
        className={cn(
          "card p-6",
          isLive && "border-grass-green/40 animate-live-pulse"
        )}
      >
        <div className="flex items-center justify-center gap-3 mb-4 text-text-secondary text-sm">
          <span>{match.league_name}</span>
          {match.matchday && <span>· MD {match.matchday}</span>}
        </div>
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
          <div className="justify-self-end text-lg">
            <TeamCard team={match.home_team} align="right" />
          </div>
          <div className="text-center">
            <ScoreBig
              home={match.home_score}
              away={match.away_score}
              className="text-4xl"
            />
            <div className="mt-2">
              {isLive ? (
                <LiveBadge />
              ) : match.status === "FINISHED" ? (
                <StatLabel>Full time</StatLabel>
              ) : (
                <div className="text-text-secondary text-sm">
                  {formatKickoffDate(match.kickoff)} ·{" "}
                  {formatKickoffTime(match.kickoff)}
                </div>
              )}
            </div>
          </div>
          <div className="justify-self-start text-lg">
            <TeamCard team={match.away_team} />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "px-4 py-2 text-sm -mb-px border-b-2 transition-colors",
              tab === t
                ? "border-grass-green text-text-primary"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Overview" && <Overview match={match} />}
      {tab === "Stats" && <Stats match={match} />}
      {tab === "Prediction" && <PredictionTab match={match} />}
      {tab === "Lineups" && (
        <p className="text-text-secondary text-sm card p-6">
          Lineups are not available for this match yet.
        </p>
      )}
    </div>
  );
}

function Overview({ match }: { match: MatchDetail }) {
  if (match.events.length === 0) {
    return (
      <p className="text-text-secondary text-sm card p-6">
        No key events recorded yet.
      </p>
    );
  }
  return (
    <div className="card p-5">
      <StatLabel>Key events</StatLabel>
      <ul className="mt-4 space-y-3">
        {match.events.map((e) => (
          <li key={e.id} className="flex items-center gap-3 text-sm">
            <span className="font-mono text-text-secondary w-10">
              {e.minute ?? "–"}&apos;
            </span>
            <span className="rounded bg-surface-raised px-2 py-0.5 text-xs">
              {e.type}
            </span>
            <span>{e.player_name || e.team?.name || ""}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Stats({ match }: { match: MatchDetail }) {
  const s = match.stats;
  if (!s) {
    return (
      <p className="text-text-secondary text-sm card p-6">
        Stats are not available for this match.
      </p>
    );
  }
  return (
    <div className="card p-5 space-y-4">
      <StatBar label="Possession" home={s.home_possession} away={s.away_possession} suffix="%" />
      <StatBar label="Shots" home={s.home_shots} away={s.away_shots} />
      <StatBar label="On target" home={s.home_shots_on_target} away={s.away_shots_on_target} />
      <StatBar label="Corners" home={s.home_corners} away={s.away_corners} />
      <StatBar label="Fouls" home={s.home_fouls} away={s.away_fouls} />
      <StatBar label="xG" home={s.home_xg} away={s.away_xg} />
    </div>
  );
}

function PredictionTab({ match }: { match: MatchDetail }) {
  if (!match.prediction) {
    return (
      <p className="text-text-secondary text-sm card p-6">
        No prediction available for this match.
      </p>
    );
  }
  return (
    <PredictionDonut
      prediction={match.prediction}
      homeName={match.home_team.name}
      awayName={match.away_team.name}
    />
  );
}
