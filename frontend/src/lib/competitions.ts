import type { ArchiveLeague, League, LeagueSeason, Standing } from "./types";

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
    // La Liga is stored as "Primera Division" (Spain) in the data
    (name.includes("primera divis") && country.includes("spain")) ||
    (name.includes("serie a") && country.includes("ital")) ||
    (name.includes("bundesliga") && !name.includes("2.")) ||
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

/* --- Linking an active competition to its historical archive ------------- */

/**
 * Active competitions and their `(history)` archive rows don't always share a
 * name (e.g. active "Primera Division" ↔ "La Liga (history)"). This maps the
 * active base name to the history base name where they differ.
 */
const HISTORY_NAME_ALIAS: Record<string, string> = {
  "primera division": "la liga",
};

function baseName(name: string): string {
  return name
    .toLowerCase()
    .replace(/\s*\(history\)\s*$/, "")
    .replace(/\s*\(statsbomb[^)]*\)\s*$/, "")
    .trim();
}

/** Find the `(history)` archive league that corresponds to an active league. */
export function findHistoryLeague(
  active: { name: string; country: string },
  archive: ArchiveLeague[]
): ArchiveLeague | null {
  const target =
    HISTORY_NAME_ALIAS[active.name.toLowerCase()] ??
    baseName(active.name);
  const country = (active.country || "").toLowerCase();
  return (
    archive.find(
      (a) =>
        a.name.toLowerCase().includes("(history)") &&
        baseName(a.name) === target &&
        (a.country || "").toLowerCase() === country
    ) ?? null
  );
}

/**
 * Find the `(StatsBomb …)` archive rows for a competition — these carry the
 * rich data (lineups, goals+assists, full stats). One row per season.
 */
export function findStatsBombLeagues(
  active: { name: string; country: string },
  archive: ArchiveLeague[]
): ArchiveLeague[] {
  const target =
    HISTORY_NAME_ALIAS[active.name.toLowerCase()] ?? baseName(active.name);
  const country = (active.country || "").toLowerCase();
  return archive.filter(
    (a) =>
      a.name.toLowerCase().includes("(statsbomb") &&
      baseName(a.name) === target &&
      (a.country || "").toLowerCase() === country
  );
}

export type SeasonSourceKind = "live" | "statsbomb" | "history";

export interface SeasonOption {
  /** season-start year as a string, e.g. "2024" */
  value: string;
  label: string;
  /** belongs to the live/active competition (vs the historical archive) */
  isLive: boolean;
  /** which league row holds this season's data */
  leagueId: number;
  matchCount: number;
  source: SeasonSourceKind;
  /** rich = full lineups, goals+assists, detailed stats (StatsBomb) */
  rich: boolean;
}

export interface SeasonSource {
  leagueId: number;
  seasons: LeagueSeason[];
  kind: SeasonSourceKind;
}

// Higher wins when the same season exists in multiple sources. StatsBomb beats
// the football-data history because it carries lineups + richer stats.
const SOURCE_PRIORITY: Record<SeasonSourceKind, number> = {
  live: 3,
  statsbomb: 2,
  history: 1,
};

/**
 * Merge seasons (those that actually have matches) from every source for a
 * competition — the live row, its StatsBomb season rows, and the football-data
 * `(history)` row — into one list, newest first.
 */
export function mergeSeasonSources(sources: SeasonSource[]): SeasonOption[] {
  const byValue = new Map<string, { opt: SeasonOption; priority: number }>();

  for (const src of sources) {
    const priority = SOURCE_PRIORITY[src.kind];
    for (const s of src.seasons) {
      const existing = byValue.get(s.season);
      if (existing && existing.priority >= priority) continue;
      byValue.set(s.season, {
        priority,
        opt: {
          value: s.season,
          label: seasonLabel(s.season),
          isLive: src.kind === "live",
          leagueId: src.leagueId,
          matchCount: s.match_count,
          source: src.kind,
          rich: src.kind === "statsbomb",
        },
      });
    }
  }

  return Array.from(byValue.values())
    .map((v) => v.opt)
    .sort((a, b) => b.value.localeCompare(a.value));
}

/**
 * UTC date range (ISO yyyy-mm-dd) covering a single football season. Runs
 * Aug–Jul to keep the COVID-extended 2019/20 season (which finished in July
 * 2020) intact — mirrors SEASON_CUTOFF_MONTH on the backend.
 */
export function seasonDateRange(season: string): {
  dateFrom: string;
  dateTo: string;
} {
  const y = parseInt(season, 10);
  return { dateFrom: `${y}-08-01`, dateTo: `${y + 1}-07-31` };
}

export type Venue = "overall" | "home" | "away";

export const VENUES: { value: Venue; label: string }[] = [
  { value: "overall", label: "Overall" },
  { value: "home", label: "Home" },
  { value: "away", label: "Away" },
];

export function normalizeVenue(value: string | undefined): Venue {
  return value === "home" || value === "away" ? value : "overall";
}
