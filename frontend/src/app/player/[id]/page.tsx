import { notFound } from "next/navigation";
import { getPlayer, getPlayerMatches } from "@/lib/api";
import EntityProfile from "@/components/profile/EntityProfile";

export const revalidate = 600;

const emptyPage = { count: 0, next: null, previous: null, results: [] };

export default async function PlayerPage({
  params,
}: {
  params: { id: string };
}) {
  let player;
  try {
    player = await getPlayer(params.id);
  } catch {
    notFound();
  }
  const matches = await getPlayerMatches(params.id).catch(() => emptyPage);

  const subtitleParts = [
    player.position,
    player.nationality,
    player.team_name,
  ].filter(Boolean);

  return (
    <EntityProfile
      eyebrow="Player"
      title={player.nickname || player.name}
      subtitle={subtitleParts.join(" · ") || undefined}
      stats={[
        { label: "Apps", value: player.appearances },
        { label: "Goals", value: player.goals, accent: true },
        { label: "Assists", value: player.assists, accent: true },
        { label: "Yellow", value: player.yellow_cards },
        { label: "Red", value: player.red_cards },
      ]}
      matches={matches.results}
      matchesTitle="Match appearances"
      emptyText="No appearances recorded."
    />
  );
}
