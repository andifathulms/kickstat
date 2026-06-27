import Link from "next/link";
import type { TeamMini } from "@/lib/types";

export default function TeamCard({
  team,
  align = "left",
}: {
  team: TeamMini;
  align?: "left" | "right";
}) {
  const content = (
    <>
      {team.logo_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={team.logo_url}
          alt={team.name}
          className="h-6 w-6 object-contain"
        />
      ) : (
        <span className="h-6 w-6 rounded-full bg-surface-raised inline-block" />
      )}
      <span className="truncate">{team.name}</span>
    </>
  );
  return (
    <Link
      href={`/team/${team.id}`}
      className={`flex items-center gap-2 hover:text-grass-green transition-colors ${
        align === "right" ? "flex-row-reverse text-right" : ""
      }`}
    >
      {content}
    </Link>
  );
}
