import Link from "next/link";
import type { Prediction, MatchListItem } from "@/lib/types";
import StatLabel from "@/components/ui/StatLabel";

const OUTCOME_COLOR = {
  HOME: "text-grass-green",
  DRAW: "text-amber-goal",
  AWAY: "text-red-card",
};

/** Compact prediction pick card (predictions hub + home "top picks"). */
export default function PredictionCard({
  prediction,
}: {
  prediction: Prediction;
}) {
  const match = prediction.match as MatchListItem;
  const pickLabel =
    prediction.predicted_outcome === "HOME"
      ? match.home_team.name
      : prediction.predicted_outcome === "AWAY"
        ? match.away_team.name
        : "Draw";

  return (
    <Link href={`/match/${match.id}`} className="card p-4 block hover:border-text-secondary/40">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-text-secondary truncate">
          {match.league_name}
        </span>
        <span className="font-mono text-sm">
          {Math.round(prediction.confidence_score * 100)}%
        </span>
      </div>
      <div className="text-sm mb-3">
        {match.home_team.name}{" "}
        <span className="text-text-secondary">vs</span> {match.away_team.name}
      </div>
      <StatLabel>Pick</StatLabel>
      <div
        className={`font-medium ${OUTCOME_COLOR[prediction.predicted_outcome]}`}
      >
        {pickLabel}
      </div>
      <div className="mt-3 flex h-1.5 overflow-hidden rounded">
        <div
          className="bg-grass-green"
          style={{ width: `${prediction.home_win_prob * 100}%` }}
        />
        <div
          className="bg-amber-goal"
          style={{ width: `${prediction.draw_prob * 100}%` }}
        />
        <div
          className="bg-red-card"
          style={{ width: `${prediction.away_win_prob * 100}%` }}
        />
      </div>
    </Link>
  );
}
