import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getMatch } from "@/lib/api";
import MatchCenter from "@/components/match/MatchCenter";

export const revalidate = 30;

export async function generateMetadata({
  params,
}: {
  params: { id: string };
}): Promise<Metadata> {
  try {
    const match = await getMatch(params.id);
    return {
      title: `${match.home_team.name} vs ${match.away_team.name} — Kickstat`,
      description: `Live score, stats, and AI prediction for ${match.home_team.name} vs ${match.away_team.name}.`,
    };
  } catch {
    return { title: "Match — Kickstat" };
  }
}

export default async function MatchPage({
  params,
}: {
  params: { id: string };
}) {
  let match;
  try {
    match = await getMatch(params.id);
  } catch {
    notFound();
  }
  return <MatchCenter match={match} />;
}
