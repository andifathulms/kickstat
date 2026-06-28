import { cn } from "@/lib/utils";

export default function ScoreBig({
  home,
  away,
  className,
  live = false,
}: {
  home: number | null;
  away: number | null;
  className?: string;
  live?: boolean;
}) {
  const display = (v: number | null) => (v === null ? "–" : v);
  return (
    <span
      className={cn(
        "font-mono font-medium tabular-nums",
        live ? "text-grass-green" : "text-text-primary",
        className
      )}
    >
      {display(home)}
      <span className="mx-1.5 text-text-muted">:</span>
      {display(away)}
    </span>
  );
}
