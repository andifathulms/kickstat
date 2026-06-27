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

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Today&apos;s AI predictions</h1>
        <p className="text-text-secondary text-sm">
          Logistic-regression picks ranked by model confidence. Predictions run
          daily at 08:00 WIB.
        </p>
      </header>

      {predictions.length === 0 ? (
        <p className="text-text-secondary text-sm">
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
