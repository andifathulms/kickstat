import { leagueInitials } from "@/lib/competitions";
import { flagUrl } from "@/lib/flags";
import { cn } from "@/lib/utils";

/**
 * Square badge for a competition. Shows the country flag when one is known,
 * otherwise a monogram (no league crests in the data).
 */
export default function CompetitionBadge({
  name,
  country,
  className,
}: {
  name: string;
  country?: string | null;
  className?: string;
}) {
  const flag = flagUrl(country);
  if (flag) {
    return (
      <span
        className={cn(
          "inline-flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-md border border-border bg-surface-raised",
          className
        )}
        aria-hidden
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={flag} alt="" className="h-full w-full object-cover" />
      </span>
    );
  }
  return (
    <span
      className={cn(
        "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-surface-raised font-mono text-xs font-medium text-text-primary",
        className
      )}
      aria-hidden
    >
      {leagueInitials(name)}
    </span>
  );
}
