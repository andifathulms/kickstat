import type { Metadata } from "next";
import { getTodayPredictions } from "@/lib/api";
import PredictionCard from "@/components/match/PredictionCard";

export const revalidate = 300;

export const metadata: Metadata = {
  title: "Predictions — Kickstat",
  description: "Today's AI match predictions with confidence levels.",
};

export default async function PredictionsPage() {
  const predictions = await getTodayPredictions().catch(() => []);
  const avgConfidence =
    predictions.length > 0
      ? Math.round(
          (predictions.reduce((s, p) => s + p.confidence_score, 0) /
            predictions.length) *
            100
        )
      : 0;

  return (
    <div className="space-y-8">
      <header className="relative overflow-hidden rounded-2xl border border-border bg-surface p-6">
        <div className="pointer-events-none absolute inset-0 bg-accent-sheen opacity-60" />
        <div className="relative">
          <span className="stat-label text-accent/90">Model</span>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            Today&apos;s AI predictions
          </h1>
          <p className="mt-1 max-w-xl text-sm text-text-secondary">
            Picks ranked by model confidence. Predictions run daily at 08:00
            WIB.
          </p>
          {predictions.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-3 text-xs">
              <span className="chip">
                <span className="font-mono text-text-primary">
                  {predictions.length}
                </span>{" "}
                fixtures
              </span>
              <span className="chip">
                <span className="font-mono text-text-primary">
                  {avgConfidence}%
                </span>{" "}
                avg confidence
              </span>
            </div>
          )}
        </div>
      </header>

      {predictions.length === 0 ? (
        <p className="card p-8 text-center text-sm text-text-secondary">
          No predictions available for today.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {predictions.map((p) => (
            <PredictionCard key={p.id} prediction={p} />
          ))}
        </div>
      )}
    </div>
  );
}
