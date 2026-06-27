import { cn } from "@/lib/utils";

export default function ScoreBig({
  home,
  away,
  className,
}: {
  home: number | null;
  away: number | null;
  className?: string;
}) {
  const display = (v: number | null) => (v === null ? "–" : v);
  return (
    <span
      className={cn(
        "font-mono font-medium tabular-nums text-text-primary",
        className
      )}
    >
      {display(home)}
      <span className="text-text-secondary mx-1.5">:</span>
      {display(away)}
    </span>
  );
}
