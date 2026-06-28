import Link from "next/link";
import type { Prediction, MatchListItem } from "@/lib/types";
import { cn } from "@/lib/utils";

const OUTCOME = {
  HOME: { color: "text-grass-green", bar: "bg-grass-green", label: "Home win" },
  DRAW: { color: "text-amber-goal", bar: "bg-amber-goal", label: "Draw" },
  AWAY: { color: "text-red-card", bar: "bg-red-card", label: "Away win" },
};

/** Compact prediction pick card (predictions hub + home "top picks"). */
export default function PredictionCard({
  prediction,
}: {
  prediction: Prediction;
}) {
  const match = prediction.match as MatchListItem;
  const o = OUTCOME[prediction.predicted_outcome];
  const pickLabel =
    prediction.predicted_outcome === "HOME"
      ? match.home_team.name
      : prediction.predicted_outcome === "AWAY"
        ? match.away_team.name
        : "Draw";
  const confidence = Math.round(prediction.confidence_score * 100);

  return (
    <Link
      href={`/match/${match.id}`}
      className="card card-hover block overflow-hidden p-4"
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="truncate text-xs text-text-secondary">
          {match.league_name}
        </span>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[11px] font-medium",
            confidence >= 60
              ? "bg-accent/15 text-accent"
              : "bg-surface-raised text-text-secondary"
          )}
        >
          {confidence}% conf.
        </span>
      </div>

      <div className="mb-3 truncate text-sm font-medium">
        {match.home_team.name}{" "}
        <span className="text-text-muted">vs</span> {match.away_team.name}
      </div>

      <div className="mb-3 flex items-baseline justify-between gap-2">
        <span className="stat-label">Model pick</span>
        <span className={cn("truncate text-sm font-semibold", o.color)}>
          {pickLabel}
        </span>
      </div>

      {/* probability split */}
      <div className="flex h-2 overflow-hidden rounded-full bg-surface-raised">
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
      <div className="mt-1.5 flex justify-between font-mono text-[10px] text-text-secondary">
        <span>{Math.round(prediction.home_win_prob * 100)}%</span>
        <span>{Math.round(prediction.draw_prob * 100)}%</span>
        <span>{Math.round(prediction.away_win_prob * 100)}%</span>
      </div>
    </Link>
  );
}
