import { notFound } from "next/navigation";
import { getStadium, getStadiumMatches } from "@/lib/api";
import EntityProfile from "@/components/profile/EntityProfile";

export const revalidate = 600;

const emptyPage = { count: 0, next: null, previous: null, results: [] };

export default async function StadiumPage({
  params,
}: {
  params: { id: string };
}) {
  let stadium;
  try {
    stadium = await getStadium(params.id);
  } catch {
    notFound();
  }
  const matches = await getStadiumMatches(params.id).catch(() => emptyPage);

  return (
    <EntityProfile
      eyebrow="Stadium"
      title={stadium.name.trim()}
      subtitle={stadium.country || undefined}
      stats={[{ label: "Matches", value: stadium.match_count }]}
      matches={matches.results}
      matchesTitle="Matches hosted"
      emptyText="No matches hosted."
    />
  );
}
