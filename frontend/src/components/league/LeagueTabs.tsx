"use client";

import { useState } from "react";
import type { League } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function LeagueTabs({
  leagues,
  children,
}: {
  leagues: League[];
  /** Render-prop: receives the active league id. */
  children: (activeLeagueId: number) => React.ReactNode;
}) {
  const [active, setActive] = useState(leagues[0]?.id ?? 0);

  if (leagues.length === 0) {
    return <p className="text-text-secondary text-sm">No leagues available.</p>;
  }

  return (
    <div>
      <div className="flex gap-1 overflow-x-auto pb-2">
        {leagues.map((l) => (
          <button
            key={l.id}
            onClick={() => setActive(l.id)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors",
              active === l.id
                ? "bg-surface-raised text-text-primary"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            {l.name}
          </button>
        ))}
      </div>
      <div className="mt-3">{children(active)}</div>
    </div>
  );
}
