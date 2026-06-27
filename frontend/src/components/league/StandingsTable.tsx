import Link from "next/link";
import type { Standing } from "@/lib/types";
import StatLabel from "@/components/ui/StatLabel";

const COLS: { key: keyof Standing | "team"; label: string }[] = [
  { key: "played", label: "P" },
  { key: "won", label: "W" },
  { key: "drawn", label: "D" },
  { key: "lost", label: "L" },
  { key: "goal_difference", label: "GD" },
  { key: "points", label: "Pts" },
];

export default function StandingsTable({
  standings,
}: {
  standings: Standing[];
}) {
  return (
    <div className="card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-3 pl-4 pr-2 w-8">
              <StatLabel>#</StatLabel>
            </th>
            <th className="text-left py-3 px-2">
              <StatLabel>Team</StatLabel>
            </th>
            {COLS.map((c) => (
              <th key={c.label} className="text-right py-3 px-2 w-10">
                <StatLabel>{c.label}</StatLabel>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {standings.map((s) => (
            <tr
              key={s.id}
              className="border-b border-border/50 last:border-0 hover:bg-surface-raised/40"
            >
              <td className="py-2.5 pl-4 pr-2 font-mono text-text-secondary">
                {s.position}
              </td>
              <td className="py-2.5 px-2">
                <Link
                  href={`/team/${s.team.id}`}
                  className="flex items-center gap-2 hover:text-grass-green"
                >
                  {s.team.logo_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={s.team.logo_url}
                      alt=""
                      className="h-5 w-5 object-contain"
                    />
                  ) : (
                    <span className="h-5 w-5 rounded-full bg-surface-raised inline-block" />
                  )}
                  <span className="truncate">{s.team.name}</span>
                </Link>
              </td>
              {COLS.map((c) => (
                <td
                  key={c.label}
                  className={`py-2.5 px-2 text-right font-mono tabular-nums ${
                    c.key === "points" ? "text-text-primary font-medium" : ""
                  }`}
                >
                  {String(s[c.key as keyof Standing])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
