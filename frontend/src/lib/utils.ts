import type { MatchListItem } from "./types";

export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

/** Format a UTC ISO kickoff to the viewer's local time (display conversion on FE). */
export function formatKickoffTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatKickoffDate(iso: string): string {
  return new Date(iso).toLocaleDateString([], {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function todayISODate(): string {
  return new Date().toISOString().slice(0, 10);
}

/** W / D / L from the perspective of `teamId` for a finished match. */
export function resultFor(
  match: MatchListItem,
  teamId: number
): "W" | "D" | "L" | null {
  if (match.home_score === null || match.away_score === null) return null;
  const isHome = match.home_team.id === teamId;
  const gf = isHome ? match.home_score : match.away_score;
  const ga = isHome ? match.away_score : match.home_score;
  if (gf > ga) return "W";
  if (gf === ga) return "D";
  return "L";
}

/** Group a list of matches by league name (preserves first-seen order). */
export function groupByLeague<T extends { league_name: string }>(
  matches: T[]
): Record<string, T[]> {
  return matches.reduce<Record<string, T[]>>((acc, m) => {
    (acc[m.league_name] ||= []).push(m);
    return acc;
  }, {});
}
