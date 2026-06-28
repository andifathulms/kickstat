import Link from "next/link";
import type { Standing } from "@/lib/types";
import { cn } from "@/lib/utils";

const COLS: {
  key: keyof Standing;
  label: string;
  em?: boolean;
  hideSm?: boolean;
}[] = [
  { key: "played", label: "P" },
  { key: "won", label: "W" },
  { key: "drawn", label: "D" },
  { key: "lost", label: "L" },
  { key: "goals_for", label: "GF", hideSm: true },
  { key: "goals_against", label: "GA", hideSm: true },
  { key: "goal_difference", label: "GD" },
  { key: "points", label: "Pts", em: true },
];

const FORM_STYLE: Record<string, string> = {
  W: "bg-grass-green/20 text-grass-green",
  D: "bg-amber-goal/20 text-amber-goal",
  L: "bg-red-card/20 text-red-card",
};

function Form({ form }: { form?: ("W" | "D" | "L")[] }) {
  if (!form || form.length === 0) {
    return <span className="text-text-muted">–</span>;
  }
  return (
    <div className="flex justify-end gap-0.5">
      {form.map((r, i) => (
        <span
          key={i}
          className={cn(
            "grid h-4 w-4 place-items-center rounded-[3px] text-[9px] font-bold",
            FORM_STYLE[r]
          )}
          title={r}
        >
          {r}
        </span>
      ))}
    </div>
  );
}

/** Accent stripe on the position cell to hint at zones (top / relegation). */
function zoneClass(position: number, total: number): string {
  if (position <= 4) return "before:bg-grass-green"; // CL-ish
  if (position <= 6) return "before:bg-amber-goal"; // Europa-ish
  if (total >= 18 && position > total - 3) return "before:bg-red-card"; // drop
  return "before:bg-transparent";
}

export default function StandingsTable({
  standings,
  showZones = true,
}: {
  standings: Standing[];
  showZones?: boolean;
}) {
  const total = standings.length;
  return (
    <div className="card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-text-secondary">
            <th className="w-10 py-3 pl-4 pr-2 text-left">
              <span className="stat-label">#</span>
            </th>
            <th className="py-3 px-2 text-left">
              <span className="stat-label">Team</span>
            </th>
            {COLS.map((c) => (
              <th
                key={c.label}
                className={cn(
                  "w-10 py-3 px-2 text-right",
                  c.hideSm && "hidden sm:table-cell"
                )}
              >
                <span className="stat-label">{c.label}</span>
              </th>
            ))}
            <th className="hidden w-28 py-3 pl-2 pr-4 text-right md:table-cell">
              <span className="stat-label">Form</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {standings.map((s) => (
            <tr
              key={s.id}
              className="border-b border-border/40 transition-colors last:border-0 hover:bg-surface-raised/50"
            >
              <td
                className={cn(
                  "relative py-2.5 pl-4 pr-2 font-mono text-text-secondary",
                  "before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-0.5 before:rounded-full",
                  showZones ? zoneClass(s.position, total) : "before:bg-transparent"
                )}
              >
                {s.position}
              </td>
              <td className="py-2.5 px-2">
                <Link
                  href={`/team/${s.team.id}`}
                  className="flex items-center gap-2.5 transition-colors hover:text-accent"
                >
                  {s.team.logo_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={s.team.logo_url}
                      alt=""
                      className="h-5 w-5 object-contain"
                    />
                  ) : (
                    <span className="h-5 w-5 rounded-full bg-surface-raised" />
                  )}
                  <span className="truncate font-medium">{s.team.name}</span>
                </Link>
              </td>
              {COLS.map((c) => (
                <td
                  key={c.label}
                  className={cn(
                    "py-2.5 px-2 text-right font-mono tabular-nums",
                    c.hideSm && "hidden sm:table-cell",
                    c.em
                      ? "font-semibold text-text-primary"
                      : "text-text-secondary"
                  )}
                >
                  {c.key === "goal_difference" && s.goal_difference > 0
                    ? `+${s.goal_difference}`
                    : String(s[c.key])}
                </td>
              ))}
              <td className="hidden py-2.5 pl-2 pr-4 md:table-cell">
                <Form form={s.form} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
