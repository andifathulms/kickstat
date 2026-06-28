import type { League, Standing } from "./types";

/**
 * Competition segmentation. The backend stores leagues as a flat list with a
 * single `season` string; the UI groups them into meaningful buckets so the
 * homepage / standings hub aren't "every league thrown together".
 */

export type CompetitionGroupId =
  | "top5"
  | "continental"
  | "indonesia"
  | "more";

export interface CompetitionGroupMeta {
  id: CompetitionGroupId;
  label: string;
  blurb: string;
  /** display order (lower = first) */
  order: number;
}

export const COMPETITION_GROUPS: Record<
  CompetitionGroupId,
  CompetitionGroupMeta
> = {
  top5: {
    id: "top5",
    label: "Top 5 Europe",
    blurb: "England · Spain · Italy · Germany · France",
    order: 0,
  },
  continental: {
    id: "continental",
    label: "Continental & International",
    blurb: "UEFA & national-team competitions",
    order: 1,
  },
  indonesia: {
    id: "indonesia",
    label: "Indonesia",
    blurb: "Liga 1",
    order: 2,
  },
  more: {
    id: "more",
    label: "More leagues",
    blurb: "Other domestic competitions",
    order: 3,
  },
};

const INTERNATIONAL_KEYWORDS = [
  "champions league",
  "europa",
  "conference league",
  "world cup",
  "euro",
  "nations league",
  "copa america",
  "libertadores",
  "super cup",
];

/** Classify a league into one of the competition groups. */
export function competitionGroupOf(league: {
  name: string;
  country: string;
}): CompetitionGroupId {
  const name = league.name.toLowerCase();
  const country = (league.country || "").toLowerCase();

  if (INTERNATIONAL_KEYWORDS.some((k) => name.includes(k))) {
    return "continental";
  }

  const isTop5 =
    (name.includes("premier league") && country.includes("england")) ||
    name.includes("la liga") ||
    name.includes("laliga") ||
    (name.includes("serie a") && country.includes("ital")) ||
    name.includes("bundesliga") ||
    name.includes("ligue 1");
  if (isTop5) return "top5";

  if (country.includes("indonesia")) return "indonesia";

  return "more";
}

export interface GroupedLeagues {
  meta: CompetitionGroupMeta;
  leagues: League[];
}

/** Bucket + order leagues for grouped display. Empty groups are dropped. */
export function groupLeagues(leagues: League[]): GroupedLeagues[] {
  const buckets = new Map<CompetitionGroupId, League[]>();
  for (const league of leagues) {
    const id = competitionGroupOf(league);
    const arr = buckets.get(id) ?? [];
    arr.push(league);
    buckets.set(id, arr);
  }
  return Array.from(buckets.entries())
    .map(([id, ls]) => ({
      meta: COMPETITION_GROUPS[id],
      leagues: ls.sort((a, b) => a.name.localeCompare(b.name)),
    }))
    .sort((a, b) => a.meta.order - b.meta.order);
}

/** A two-letter flag-ish badge fallback (e.g. "PL", "LL") from a league name. */
export function leagueInitials(name: string): string {
  const words = name.replace(/[^a-zA-Z0-9 ]/g, "").split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

/* --- Seasons ------------------------------------------------------------- */

/** Render a season-start year as a "YY/YY" label, e.g. "2024" -> "24/25". */
export function seasonLabel(season: string): string {
  const start = parseInt(season, 10);
  if (Number.isNaN(start)) return season;
  const end = (start + 1) % 100;
  return `${String(start % 100).padStart(2, "0")}/${String(end).padStart(
    2,
    "0"
  )}`;
}

/** Distinct seasons present in a standings list, newest first. */
export function seasonsFromStandings(standings: Standing[]): string[] {
  const set = new Set(standings.map((s) => s.season).filter(Boolean));
  return Array.from(set).sort((a, b) => b.localeCompare(a));
}

export function standingsForSeason(
  standings: Standing[],
  season: string
): Standing[] {
  return standings
    .filter((s) => s.season === season)
    .sort((a, b) => a.position - b.position);
}
