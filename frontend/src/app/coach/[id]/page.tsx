import { notFound } from "next/navigation";
import { getCoach, getCoachMatches } from "@/lib/api";
import EntityProfile from "@/components/profile/EntityProfile";

export const revalidate = 600;

const emptyPage = { count: 0, next: null, previous: null, results: [] };

export default async function CoachPage({
  params,
}: {
  params: { id: string };
}) {
  let coach;
  try {
    coach = await getCoach(params.id);
  } catch {
    notFound();
  }
  const matches = await getCoachMatches(params.id).catch(() => emptyPage);

  const subtitleParts = [
    coach.nationality,
    coach.teams.map((t) => t.name).join(", "),
  ].filter(Boolean);

  return (
    <EntityProfile
      eyebrow="Manager"
      title={coach.name}
      subtitle={subtitleParts.join(" · ") || undefined}
      stats={[
        { label: "Played", value: coach.played },
        { label: "Won", value: coach.won, accent: true },
        { label: "Drawn", value: coach.drawn },
        { label: "Lost", value: coach.lost },
      ]}
      matches={matches.results}
      matchesTitle="Matches managed"
      emptyText="No matches managed."
    />
  );
}
