import type { MatchStats } from "@/lib/types";

type Pair = { label: string; h: keyof MatchStats; a: keyof MatchStats; pct?: boolean };

const PAIRS: Pair[] = [
  { label: "Poss", h: "home_possession", a: "away_possession", pct: true },
  { label: "Shots", h: "home_shots", a: "away_shots" },
  { label: "On tgt", h: "home_shots_on_target", a: "away_shots_on_target" },
  { label: "Corners", h: "home_corners", a: "away_corners" },
  { label: "Fouls", h: "home_fouls", a: "away_fouls" },
  { label: "Yellow", h: "home_yellow_cards", a: "away_yellow_cards" },
  { label: "Red", h: "home_red_cards", a: "away_red_cards" },
  { label: "xG", h: "home_xg", a: "away_xg" },
];

/** Compact chips of the per-match stats we acquired (only the ones present). */
export default function MatchStatsInline({ stats }: { stats: MatchStats | null }) {
  if (!stats) return null;
  const chips = PAIRS.filter((p) => stats[p.h] !== null || stats[p.a] !== null);
  if (chips.length === 0) return null;

  const fmt = (v: number | null, pct?: boolean) =>
    v === null ? "–" : pct ? `${Math.round(v)}%` : v;

  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
      {chips.map((p) => (
        <span key={p.label} className="text-[11px] text-text-secondary">
          <span className="uppercase tracking-wide">{p.label}</span>{" "}
          <span className="font-mono text-text-primary">
            {fmt(stats[p.h] as number | null, p.pct)}–{fmt(stats[p.a] as number | null, p.pct)}
          </span>
        </span>
      ))}
    </div>
  );
}
