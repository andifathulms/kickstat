import Link from "next/link";
import type { SeasonOption } from "@/lib/competitions";
import { cn } from "@/lib/utils";

/**
 * Link-based season switcher for a competition page. Updates `?season=` so the
 * whole page (standings + matches) re-renders for the chosen season — no need
 * to detour through the Archive.
 */
export default function SeasonTabs({
  seasons,
  active,
  slug,
}: {
  seasons: SeasonOption[];
  active: string;
  slug: string;
}) {
  if (seasons.length <= 1) return null;
  return (
    <div className="flex items-center gap-2">
      <span className="stat-label hidden shrink-0 sm:inline">Season</span>
      <div className="flex gap-1.5 overflow-x-auto pb-1">
        {seasons.map((s) => (
          <Link
            key={s.value}
            href={
              s.isCurrent
                ? `/league/${slug}`
                : `/league/${slug}?season=${s.value}`
            }
            scroll={false}
            className={cn(
              "pill font-mono text-xs",
              s.value === active ? "pill-active" : "pill-idle"
            )}
          >
            {s.label}
            {s.isCurrent && (
              <span
                className={cn(
                  "ml-1 h-1.5 w-1.5 rounded-full",
                  s.value === active ? "bg-accent-ink" : "bg-grass-green"
                )}
                title="Current season"
              />
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
