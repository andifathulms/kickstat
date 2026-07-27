import { Fragment } from "react";
import Link from "next/link";
import type { MatchDetail, MatchEvent } from "@/lib/types";
import { cn } from "@/lib/utils";
import StatLabel from "@/components/ui/StatLabel";

const TIMELINE_TYPES = new Set([
  "GOAL",
  "OWN_GOAL",
  "YELLOW",
  "RED",
  "SUBSTITUTION",
  "VAR",
]);

const SCORING_TYPES = new Set(["GOAL", "OWN_GOAL"]);

function PlayerLink({
  id,
  name,
  className,
}: {
  id: number | null;
  name: string | null;
  className?: string;
}) {
  if (!name) return null;
  return id ? (
    <Link href={`/player/${id}`} className={cn("hover:text-accent", className)}>
      {name}
    </Link>
  ) : (
    <span className={className}>{name}</span>
  );
}

function EventIcon({ type }: { type: MatchEvent["type"] }) {
  switch (type) {
    case "GOAL":
      return <span className="text-sm leading-none">⚽</span>;
    case "OWN_GOAL":
      return (
        <span className="text-sm leading-none opacity-60" title="Own goal">
          ⚽
        </span>
      );
    case "YELLOW":
      return <span className="inline-block h-3.5 w-2.5 rounded-[2px] bg-amber-goal" />;
    case "RED":
      return <span className="inline-block h-3.5 w-2.5 rounded-[2px] bg-red-card" />;
    case "SUBSTITUTION":
      return <span className="font-mono text-xs leading-none text-grass-green">⇄</span>;
    default:
      return <span className="stat-label">VAR</span>;
  }
}

/** Goal subtitle: assist, penalty, own goal — plus xG when we have it. */
function goalNote(e: MatchEvent) {
  const bits: string[] = [];
  if (e.type === "OWN_GOAL") bits.push("own goal");
  if (e.detail.penalty === true) bits.push("penalty");
  const xg = e.detail.xg;
  if (typeof xg === "number" && xg > 0) bits.push(`${xg.toFixed(2)} xG`);
  return bits;
}

function EventBody({ e, align }: { e: MatchEvent; align: "left" | "right" }) {
  const alignment = align === "right" ? "text-right" : "text-left";

  if (e.type === "SUBSTITUTION") {
    // The model stores the player going off in `player` and the one coming on
    // in `assist`; `detail` only carries them for StatsBomb-sourced matches.
    const on = (e.detail.player_on as string) || e.assist_name;
    const off = (e.detail.player_off as string) || e.player_name;
    return (
      <div className={cn("space-y-0.5", alignment)}>
        {on && (
          <div className="truncate text-sm font-medium">
            <span className="mr-1 text-grass-green">↑</span>
            <PlayerLink id={e.assist_id} name={on} />
          </div>
        )}
        {off && (
          <div className="truncate text-xs text-text-secondary">
            <span className="mr-1 text-red-card">↓</span>
            <PlayerLink id={e.player_id} name={off} />
          </div>
        )}
      </div>
    );
  }

  const notes = SCORING_TYPES.has(e.type) ? goalNote(e) : [];
  return (
    <div className={cn("space-y-0.5", alignment)}>
      <div className="truncate text-sm font-medium">
        <PlayerLink id={e.player_id} name={e.player_name} />
      </div>
      {e.type === "GOAL" && e.assist_name && (
        <div className="truncate text-xs text-text-secondary">
          assist: <PlayerLink id={e.assist_id} name={e.assist_name} />
        </div>
      )}
      {notes.length > 0 && (
        <div className="truncate text-xs text-text-muted">{notes.join(" · ")}</div>
      )}
    </div>
  );
}

function Divider({ label, score }: { label: string; score?: string }) {
  return (
    <li className="flex items-center gap-3 py-2">
      <span className="h-px flex-1 bg-border/60" />
      <span className="stat-label whitespace-nowrap">
        {label}
        {score && <span className="ml-2 font-mono tabular-nums">{score}</span>}
      </span>
      <span className="h-px flex-1 bg-border/60" />
    </li>
  );
}

/**
 * Vertical match timeline; home events on the left, away on the right, with a
 * running score down the middle so the shape of the match is readable at a
 * glance. Events whose minute is unknown (Understat reports cards without one)
 * are collected underneath rather than shown as a blank minute.
 */
export default function MatchTimeline({ match }: { match: MatchDetail }) {
  const relevant = match.events.filter((e) => TIMELINE_TYPES.has(e.type));
  const timed = relevant
    .filter((e) => e.minute != null)
    .sort((a, b) => (a.minute ?? 0) - (b.minute ?? 0));
  const untimed = relevant.filter((e) => e.minute == null);

  if (relevant.length === 0) {
    return (
      <p className="card p-8 text-center text-sm text-text-secondary">
        No key events recorded for this match.
      </p>
    );
  }

  // Running score, so each goal shows the scoreline it produced. An own goal
  // is stored against the team that scored it, so it counts for the opponent.
  let home = 0;
  let away = 0;
  const rows = timed.map((e) => {
    const isHome = e.team === match.home_team.id;
    if (SCORING_TYPES.has(e.type)) {
      const scoresForHome = e.type === "OWN_GOAL" ? !isHome : isHome;
      if (scoresForHome) home += 1;
      else away += 1;
    }
    return { e, isHome, score: `${home}–${away}` };
  });

  const firstSecondHalf = rows.findIndex((r) => (r.e.minute ?? 0) > 45);
  const halfTimeScore =
    firstSecondHalf > 0 ? rows[firstSecondHalf - 1].score : "0–0";

  return (
    <div className="space-y-4">
      <div className="card p-4 sm:p-6">
        <ul>
          {rows.map((row, i) => (
            <Fragment key={row.e.id}>
              {i === firstSecondHalf && (
                <Divider label="Half time" score={halfTimeScore} />
              )}
              <li
                className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-lg px-1 py-1.5 hover:bg-surface-raised/40"
              >
                <div className="min-w-0">
                  {row.isHome && <EventBody e={row.e} align="right" />}
                </div>
                <div className="flex w-[5.5rem] items-center justify-center gap-2">
                  <span className="font-mono text-xs text-text-secondary tabular-nums">
                    {row.e.minute}&apos;
                  </span>
                  <EventIcon type={row.e.type} />
                  {SCORING_TYPES.has(row.e.type) && (
                    <span className="rounded bg-surface-raised px-1.5 py-0.5 font-mono text-xs font-medium tabular-nums">
                      {row.score}
                    </span>
                  )}
                </div>
                <div className="min-w-0">
                  {!row.isHome && <EventBody e={row.e} align="left" />}
                </div>
              </li>
            </Fragment>
          ))}
          <Divider
            label="Full time"
            score={`${match.home_score ?? 0}–${match.away_score ?? 0}`}
          />
        </ul>
      </div>

      {untimed.length > 0 && (
        <div className="card p-4 sm:p-6">
          <StatLabel>Bookings — minute not recorded</StatLabel>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {untimed.map((e) => (
              <li key={e.id} className="flex items-center gap-2 text-sm">
                <EventIcon type={e.type} />
                <PlayerLink id={e.player_id} name={e.player_name} />
                <span className="ml-auto truncate text-xs text-text-secondary">
                  {e.team === match.home_team.id
                    ? match.home_team.name
                    : match.away_team.name}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
