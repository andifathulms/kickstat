export type MatchStatus =
  | "SCHEDULED"
  | "LIVE"
  | "FINISHED"
  | "POSTPONED"
  | "CANCELLED";

export type Outcome = "HOME" | "DRAW" | "AWAY";

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface League {
  id: number;
  name: string;
  slug: string;
  country: string;
  source: string;
  season: string;
  is_active: boolean;
}

export interface TeamMini {
  id: number;
  name: string;
  short_name: string;
  logo_url: string;
}

export interface Standing {
  id: number;
  season: string;
  position: number;
  team: TeamMini;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
  /** last-5 results, chronological (oldest → newest) */
  form?: ("W" | "D" | "L")[];
  /** true when derived from match results rather than synced from a source */
  computed?: boolean;
}

export interface LeagueSeason {
  season: string;
  match_count: number;
}

export interface MatchStats {
  home_possession: number | null;
  away_possession: number | null;
  home_shots: number | null;
  away_shots: number | null;
  home_shots_on_target: number | null;
  away_shots_on_target: number | null;
  home_corners: number | null;
  away_corners: number | null;
  home_fouls: number | null;
  away_fouls: number | null;
  home_yellow_cards: number | null;
  away_yellow_cards: number | null;
  home_red_cards: number | null;
  away_red_cards: number | null;
  home_xg: number | null;
  away_xg: number | null;
  extra?: { home: SideStats; away: SideStats } | null;
}

export type MatchEventType =
  | "GOAL"
  | "OWN_GOAL"
  | "YELLOW"
  | "RED"
  | "SUBSTITUTION"
  | "VAR";

export interface MatchEvent {
  id: number;
  minute: number | null;
  type: MatchEventType;
  /** team id (null if unknown) */
  team: number | null;
  player_name: string | null;
  assist_name: string | null;
  detail: Record<string, unknown>;
}

export interface MatchLineupEntry {
  team: number;
  player_id: number;
  player_name: string;
  player_nickname: string;
  shirt_number: number | null;
  position: string;
  is_starter: boolean;
  subbed_on_minute: number | null;
  subbed_off_minute: number | null;
}

export type SideStats = Record<string, number | null>;

export interface Prediction {
  id: number;
  match: number | MatchListItem;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  predicted_outcome: Outcome;
  model_version: string;
  confidence_score: number;
  was_correct: boolean | null;
  created_at: string;
}

export interface MatchListItem {
  id: number;
  league: number;
  league_name: string;
  league_slug: string;
  matchday: number | null;
  kickoff: string;
  status: MatchStatus;
  home_team: TeamMini;
  away_team: TeamMini;
  home_score: number | null;
  away_score: number | null;
}

export interface TopScore {
  home: number;
  away: number;
  prob: number;
}

export interface ScorePrediction {
  lambda_home: number;
  lambda_away: number;
  most_likely_home: number;
  most_likely_away: number;
  most_likely_prob: number;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  over25_prob: number;
  btts_prob: number;
  top_scores: TopScore[];
  model_version: string;
}

export interface MatchDetail extends Omit<MatchListItem, "league"> {
  league: League;
  referee: string;
  stadium: string;
  home_manager: string;
  away_manager: string;
  stats: MatchStats | null;
  odds: MatchOdds | null;
  events: MatchEvent[];
  lineups: MatchLineupEntry[];
  prediction: Prediction | null;
  score_prediction: ScorePrediction | null;
}

export interface ImpliedProbabilities {
  home: number;
  draw: number;
  away: number;
}

export interface MatchOdds {
  home_odds: number | null;
  draw_odds: number | null;
  away_odds: number | null;
  over25_odds: number | null;
  under25_odds: number | null;
  source: string;
  implied_probabilities: ImpliedProbabilities | null;
}

export interface MatchWithStats extends MatchListItem {
  stats: MatchStats | null;
  odds: MatchOdds | null;
}

export interface ArchiveLeague {
  id: number;
  name: string;
  slug: string;
  country: string;
  match_count: number;
  first_year: number | null;
  last_year: number | null;
}
