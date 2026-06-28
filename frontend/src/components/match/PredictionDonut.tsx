"use client";

import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import type { Prediction } from "@/lib/types";
import StatLabel from "@/components/ui/StatLabel";

const COLORS = {
  HOME: "#34D399", // grass-green
  DRAW: "#FBBF24", // amber-goal
  AWAY: "#F87171", // red-card
};

export default function PredictionDonut({
  prediction,
  homeName,
  awayName,
}: {
  prediction: Prediction;
  homeName: string;
  awayName: string;
}) {
  const data = [
    { key: "HOME", label: homeName, value: prediction.home_win_prob },
    { key: "DRAW", label: "Draw", value: prediction.draw_prob },
    { key: "AWAY", label: awayName, value: prediction.away_win_prob },
  ];
  const pct = (v: number) => `${Math.round(v * 100)}%`;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <StatLabel>AI Prediction</StatLabel>
        <span className="text-[11px] text-text-secondary font-mono">
          {prediction.model_version}
        </span>
      </div>

      <div className="flex items-center gap-6">
        <div className="relative h-36 w-36 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                innerRadius={48}
                outerRadius={68}
                startAngle={90}
                endAngle={-270}
                stroke="none"
              >
                {data.map((d) => (
                  <Cell key={d.key} fill={COLORS[d.key as keyof typeof COLORS]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-xl">
              {pct(prediction.confidence_score)}
            </span>
            <StatLabel>conf</StatLabel>
          </div>
        </div>

        <ul className="space-y-2 flex-1">
          {data.map((d) => (
            <li key={d.key} className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ background: COLORS[d.key as keyof typeof COLORS] }}
                />
                <span className="truncate max-w-[140px]">{d.label}</span>
              </span>
              <span className="font-mono tabular-nums">{pct(d.value)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
