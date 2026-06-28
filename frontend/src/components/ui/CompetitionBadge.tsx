import { leagueInitials } from "@/lib/competitions";
import { cn } from "@/lib/utils";

/** Square monogram badge for a competition (no league crests in the data). */
export default function CompetitionBadge({
  name,
  className,
}: {
  name: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-md border border-border bg-surface-raised font-mono text-xs font-medium text-text-primary",
        "h-8 w-8",
        className
      )}
      aria-hidden
    >
      {leagueInitials(name)}
    </span>
  );
}
