import { notFound } from "next/navigation";
import { getReferee, getRefereeMatches } from "@/lib/api";
import EntityProfile from "@/components/profile/EntityProfile";

export const revalidate = 600;

const emptyPage = { count: 0, next: null, previous: null, results: [] };

export default async function RefereePage({
  params,
}: {
  params: { id: string };
}) {
  let referee;
  try {
    referee = await getReferee(params.id);
  } catch {
    notFound();
  }
  const matches = await getRefereeMatches(params.id).catch(() => emptyPage);

  return (
    <EntityProfile
      eyebrow="Referee"
      title={referee.name}
      subtitle={referee.country || undefined}
      stats={[{ label: "Matches", value: referee.match_count }]}
      matches={matches.results}
      matchesTitle="Matches officiated"
      emptyText="No matches officiated."
    />
  );
}
