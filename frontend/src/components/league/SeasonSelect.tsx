"use client";

import { seasonLabel } from "@/lib/competitions";
import { cn } from "@/lib/utils";

/** Controlled pill row for switching between available seasons. */
export default function SeasonSelect({
  seasons,
  value,
  onChange,
  className,
}: {
  seasons: string[];
  value: string;
  onChange: (season: string) => void;
  className?: string;
}) {
  if (seasons.length <= 1) {
    return seasons.length === 1 ? (
      <span className={cn("chip font-mono", className)}>
        Season {seasonLabel(seasons[0])}
      </span>
    ) : null;
  }
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <span className="stat-label mr-1 hidden sm:inline">Season</span>
      <div className="flex gap-1 overflow-x-auto">
        {seasons.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onChange(s)}
            className={cn(
              "pill font-mono text-xs",
              s === value ? "pill-active" : "pill-idle"
            )}
          >
            {seasonLabel(s)}
          </button>
        ))}
      </div>
    </div>
  );
}
