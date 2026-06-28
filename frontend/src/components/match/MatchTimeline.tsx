import type { MatchDetail, MatchEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const TIMELINE_TYPES = new Set([
  "GOAL",
  "OWN_GOAL",
  "YELLOW",
  "RED",
  "SUBSTITUTION",
  "VAR",
]);

function EventIcon({ type }: { type: MatchEvent["type"] }) {
  switch (type) {
    case "GOAL":
      return <span className="text-sm">⚽</span>;
    case "OWN_GOAL":
      return (
        <span className="text-sm" title="Own goal">
          ⚽
        </span>
      );
    case "YELLOW":
      return <span className="inline-block h-3 w-2.5 rounded-[2px] bg-amber-goal" />;
    case "RED":
      return <span className="inline-block h-3 w-2.5 rounded-[2px] bg-red-card" />;
    case "SUBSTITUTION":
      return (
        <span className="font-mono text-xs text-grass-green">⇄</span>
      );
    default:
      return <span className="stat-label">VAR</span>;
  }
}

function EventBody({ e, align }: { e: MatchEvent; align: "left" | "right" }) {
  const main =
    e.type === "SUBSTITUTION"
      ? (e.detail.player_on as string) || e.player_name
      : e.player_name;
  const sub =
    e.type === "SUBSTITUTION"
      ? `↓ ${(e.detail.player_off as string) ?? e.player_name ?? ""}`
      : e.type === "GOAL" && e.assist_name
        ? `assist: ${e.assist_name}`
        : e.type === "OWN_GOAL"
          ? "own goal"
          : e.type === "GOAL" && e.detail.penalty
            ? "penalty"
            : null;
  return (
    <div className={cn(align === "right" ? "text-right" : "text-left")}>
      <div className="truncate text-sm font-medium">{main}</div>
      {sub && (
        <div className="truncate text-xs text-text-secondary">{sub}</div>
      )}
    </div>
  );
}

/** Vertical match timeline; home events on the left, away on the right. */
export default function MatchTimeline({ match }: { match: MatchDetail }) {
  const events = match.events
    .filter((e) => TIMELINE_TYPES.has(e.type))
    .sort((a, b) => (a.minute ?? 0) - (b.minute ?? 0));

  if (events.length === 0) {
    return (
      <p className="card p-8 text-center text-sm text-text-secondary">
        No key events recorded for this match.
      </p>
    );
  }

  return (
    <div className="card p-4 sm:p-6">
      <ul className="space-y-1">
        {events.map((e) => {
          const isHome = e.team === match.home_team.id;
          return (
            <li
              key={e.id}
              className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-lg px-1 py-1.5 hover:bg-surface-raised/40"
            >
              <div className="min-w-0">
                {isHome && <EventBody e={e} align="right" />}
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs text-text-secondary tabular-nums">
                  {e.minute ?? "–"}&apos;
                </span>
                <EventIcon type={e.type} />
              </div>
              <div className="min-w-0">
                {!isHome && <EventBody e={e} align="left" />}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
