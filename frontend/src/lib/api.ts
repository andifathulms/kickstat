import type {
  League,
  MatchDetail,
  MatchListItem,
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

// Leagues
export const getLeagues = () => get<Paginated<League>>("/leagues/");
export const getLeague = (idOrSlug: string | number) =>
  get<League>(`/leagues/${idOrSlug}/`);
export const getStandings = (idOrSlug: string | number) =>
  get<Standing[]>(`/leagues/${idOrSlug}/standings/`);
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

// Predictions
export const getTodayPredictions = () =>
  get<Prediction[]>("/predictions/today/");

// Teams
export const getTeamForm = (id: string | number) =>
  get<MatchListItem[]>(`/teams/${id}/form/`);
export const getTeamFixtures = (id: string | number) =>
  get<MatchListItem[]>(`/teams/${id}/fixtures/`);

export { API_URL };
