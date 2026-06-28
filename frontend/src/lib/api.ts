import type {
  ArchiveLeague,
  League,
  LeagueSeason,
  MatchDetail,
  MatchListItem,
  MatchWithStats,
  Paginated,
  Prediction,
  Standing,
} from "./types";

// Browser calls go to the publicly-published backend URL; server-side rendering
// (inside the frontend container) must reach the backend over the internal Docker
// network. INTERNAL_API_URL covers the latter and is only read on the server.
const PUBLIC_API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_URL =
  typeof window === "undefined"
    ? process.env.INTERNAL_API_URL || PUBLIC_API_URL
    : PUBLIC_API_URL;

type FetchOpts = { revalidate?: number };

async function get<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const url = `${API_URL}/api${path}`;
  const res = await fetch(url, {
    next: { revalidate: opts.revalidate ?? 60 },
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status} for ${url}`);
  }
  return res.json() as Promise<T>;
}

// Leagues — only the current-season active competitions (the full set fits in
// one page; the default unfiltered list is dominated by archived history rows).
export const getLeagues = () =>
  get<Paginated<League>>("/leagues/?is_active=true");
export const getLeague = (idOrSlug: string | number) =>
  get<League>(`/leagues/${idOrSlug}/`);
export const getStandings = (idOrSlug: string | number, season?: string) =>
  get<Standing[]>(
    `/leagues/${idOrSlug}/standings/${season ? `?season=${season}` : ""}`
  );
export const getLeagueSeasons = (idOrSlug: string | number) =>
  get<LeagueSeason[]>(`/leagues/${idOrSlug}/seasons/`, { revalidate: 600 });
export const getLeagueFixtures = (idOrSlug: string | number) =>
  get<Paginated<MatchListItem>>(`/leagues/${idOrSlug}/fixtures/`);
export const getLeagueResults = (idOrSlug: string | number) =>
  get<Paginated<MatchListItem>>(`/leagues/${idOrSlug}/results/`);

// Matches
export const getMatches = (query = "") =>
  get<Paginated<MatchListItem>>(`/matches/${query}`);
export const getLiveMatches = () =>
  get<MatchListItem[]>("/matches/live/", { revalidate: 0 });
export const getMatch = (id: string | number) =>
  get<MatchDetail>(`/matches/${id}/`, { revalidate: 30 });
export const getMatchesByDate = (date: string) =>
  get<Paginated<MatchListItem>>(`/matches/?date=${date}`);

// Archive / history
export const getArchiveLeagues = () =>
  get<ArchiveLeague[]>("/leagues/archive/", { revalidate: 600 });

export function getHistoryMatches(params: {
  league: number;
  page?: number;
  dateFrom?: string;
  dateTo?: string;
}) {
  const q = new URLSearchParams({
    league: String(params.league),
    with_stats: "true",
    ordering: "-kickoff",
    page: String(params.page ?? 1),
  });
  if (params.dateFrom) q.set("date_from", params.dateFrom);
  if (params.dateTo) q.set("date_to", params.dateTo);
  return get<Paginated<MatchWithStats>>(`/matches/?${q.toString()}`, {
    revalidate: 600,
  });
}

// Predictions
export const getTodayPredictions = () =>
  get<Prediction[]>("/predictions/today/");

// Teams
export const getTeamForm = (id: string | number) =>
  get<MatchListItem[]>(`/teams/${id}/form/`);
export const getTeamFixtures = (id: string | number) =>
  get<MatchListItem[]>(`/teams/${id}/fixtures/`);

export { API_URL };
