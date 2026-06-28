import type { MatchOdds } from "@/lib/types";
import StatLabel from "@/components/ui/StatLabel";

const pct = (v: number) => `${Math.round(v * 100)}%`;

/** Pre-match bookmaker odds → market-implied (de-vigged) win probabilities. */
export default function MarketOdds({
  odds,
  compact = false,
}: {
  odds: MatchOdds | null;
  compact?: boolean;
}) {
  const p = odds?.implied_probabilities;
  if (!p) return null;

  if (compact) {
    return (
      <div className="mt-2 flex items-center gap-2">
        <span className="text-[11px] uppercase tracking-wide text-text-secondary">
          Mkt
        </span>
        <div className="flex h-1.5 flex-1 overflow-hidden rounded">
          <div className="bg-grass-green" style={{ width: pct(p.home) }} />
          <div className="bg-amber-goal" style={{ width: pct(p.draw) }} />
          <div className="bg-red-card" style={{ width: pct(p.away) }} />
        </div>
        <span className="font-mono text-[11px] text-text-secondary">
          {pct(p.home)}/{pct(p.draw)}/{pct(p.away)}
        </span>
      </div>
    );
  }

  const rows = [
    { label: "Home", prob: p.home, odd: odds?.home_odds, color: "#34D399" },
    { label: "Draw", prob: p.draw, odd: odds?.draw_odds, color: "#FBBF24" },
    { label: "Away", prob: p.away, odd: odds?.away_odds, color: "#F87171" },
  ];
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <StatLabel>Market odds</StatLabel>
        <span className="text-[11px] text-text-secondary">{odds?.source}</span>
      </div>
      <ul className="space-y-2">
        {rows.map((r) => (
          <li key={r.label} className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ background: r.color }}
              />
              {r.label}
            </span>
            <span className="flex items-center gap-3 font-mono tabular-nums">
              <span className="text-text-secondary">{r.odd ?? "–"}</span>
              <span>{pct(r.prob)}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
