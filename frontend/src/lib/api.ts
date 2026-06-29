import type {
  ArchiveLeague,
  CoachDetail,
  League,
  LeagueSeason,
  MatchDetail,
  MatchListItem,
  MatchWithStats,
  Paginated,
  PlayerDetail,
  Prediction,
  RefereeDetail,
  SearchResults,
  Standing,
  StadiumDetail,
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
export const getStandings = (
  idOrSlug: string | number,
  season?: string,
  venue?: string
) => {
  const q = new URLSearchParams();
  if (season) q.set("season", season);
  if (venue && venue !== "overall") q.set("venue", venue);
  const qs = q.toString();
  return get<Standing[]>(`/leagues/${idOrSlug}/standings/${qs ? `?${qs}` : ""}`);
};
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

// Search
export const search = (q: string) =>
  get<SearchResults>(`/search/?q=${encodeURIComponent(q)}`, { revalidate: 0 });

// People / venues
export const getReferee = (id: string | number) =>
  get<RefereeDetail>(`/referees/${id}/`);
export const getStadium = (id: string | number) =>
  get<StadiumDetail>(`/stadiums/${id}/`);
export const getCoach = (id: string | number) =>
  get<CoachDetail>(`/coaches/${id}/`);
export const getPlayer = (id: string | number) =>
  get<PlayerDetail>(`/players/${id}/`);

const entityMatches = (kind: string, id: string | number, page = 1) =>
  get<Paginated<MatchListItem>>(`/${kind}/${id}/matches/?page=${page}`);
export const getRefereeMatches = (id: string | number, page = 1) =>
  entityMatches("referees", id, page);
export const getStadiumMatches = (id: string | number, page = 1) =>
  entityMatches("stadiums", id, page);
export const getCoachMatches = (id: string | number, page = 1) =>
  entityMatches("coaches", id, page);
export const getPlayerMatches = (id: string | number, page = 1) =>
  entityMatches("players", id, page);

export { API_URL };
