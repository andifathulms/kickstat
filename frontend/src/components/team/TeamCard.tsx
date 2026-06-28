import Link from "next/link";
import type { TeamMini } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function TeamCard({
  team,
  align = "left",
}: {
  team: TeamMini;
  align?: "left" | "right";
}) {
  const logo = team.logo_url ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={team.logo_url}
      alt=""
      className="h-7 w-7 shrink-0 object-contain"
    />
  ) : (
    <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-surface-raised text-[10px] font-medium text-text-secondary">
      {team.short_name?.slice(0, 3) || team.name.slice(0, 2)}
    </span>
  );

  return (
    <Link
      href={`/team/${team.id}`}
      className={cn(
        "group flex min-w-0 items-center gap-2.5 transition-colors hover:text-accent",
        align === "right" && "flex-row-reverse text-right"
      )}
    >
      {logo}
      <span className="truncate font-medium">{team.name}</span>
    </Link>
  );
}
