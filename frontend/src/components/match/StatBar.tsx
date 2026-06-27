import StatLabel from "@/components/ui/StatLabel";

/** Horizontal comparison bar for a single stat (e.g. possession, shots). */
export default function StatBar({
  label,
  home,
  away,
  suffix = "",
}: {
  label: string;
  home: number | null;
  away: number | null;
  suffix?: string;
}) {
  const h = home ?? 0;
  const a = away ?? 0;
  const total = h + a;
  const homePct = total > 0 ? (h / total) * 100 : 50;

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="font-mono text-sm tabular-nums">
          {home ?? "–"}
          {suffix}
        </span>
        <StatLabel>{label}</StatLabel>
        <span className="font-mono text-sm tabular-nums">
          {away ?? "–"}
          {suffix}
        </span>
      </div>
      <div className="flex h-1.5 gap-0.5">
        <div className="bg-surface-raised rounded-l overflow-hidden flex-1 flex justify-end">
          <div
            className="h-full bg-grass-green rounded-l"
            style={{ width: `${homePct}%` }}
          />
        </div>
        <div className="bg-surface-raised rounded-r overflow-hidden flex-1">
          <div
            className="h-full bg-amber-goal rounded-r"
            style={{ width: `${100 - homePct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
