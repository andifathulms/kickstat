import type { ScorePrediction } from "@/lib/types";
import StatLabel from "@/components/ui/StatLabel";

const pct = (v: number) => `${Math.round(v * 100)}%`;

/** Poisson scoreline model: most-likely score, expected goals, top scorelines,
    and distribution-derived markets. */
export default function ScorelinePanel({
  score,
  homeName,
  awayName,
}: {
  score: ScorePrediction;
  homeName: string;
  awayName: string;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <StatLabel>Most likely score</StatLabel>
        <span className="text-[11px] text-text-secondary">{score.model_version}</span>
      </div>

      {/* Headline most-likely score */}
      <div className="text-center mb-4">
        <span className="font-mono text-3xl font-medium">
          {score.most_likely_home}
          <span className="text-text-secondary mx-2">–</span>
          {score.most_likely_away}
        </span>
        <div className="text-xs text-text-secondary mt-1">
          {pct(score.most_likely_prob)} likely · xG {score.lambda_home.toFixed(2)}–
          {score.lambda_away.toFixed(2)}
        </div>
      </div>

      {/* Top scorelines */}
      <ul className="space-y-1.5 mb-4">
        {score.top_scores.map((s, i) => (
          <li key={i} className="flex items-center gap-3 text-sm">
            <span className="font-mono w-12 text-center">
              {s.home}–{s.away}
            </span>
            <div className="flex-1 h-1.5 bg-surface-raised rounded overflow-hidden">
              <div
                className="h-full bg-grass-green"
                style={{ width: pct(s.prob / score.top_scores[0].prob) }}
              />
            </div>
            <span className="font-mono text-xs text-text-secondary w-9 text-right">
              {pct(s.prob)}
            </span>
          </li>
        ))}
      </ul>

      {/* Markets */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <Market label="Over 2.5" value={pct(score.over25_prob)} />
        <Market label="BTTS" value={pct(score.btts_prob)} />
        <Market
          label="1X2"
          value={`${pct(score.home_win_prob)}/${pct(score.draw_prob)}/${pct(
            score.away_win_prob
          )}`}
        />
      </div>
    </div>
  );
}

function Market({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-surface-raised px-2 py-2">
      <StatLabel className="block">{label}</StatLabel>
      <div className="font-mono text-sm mt-0.5">{value}</div>
    </div>
  );
}
