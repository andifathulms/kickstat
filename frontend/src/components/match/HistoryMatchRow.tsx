import Link from "next/link";
import type { MatchWithStats } from "@/lib/types";
import { formatKickoffDate } from "@/lib/utils";
import ScoreBig from "@/components/ui/ScoreBig";
import MatchStatsInline from "@/components/match/MatchStatsInline";

/** A finished historical match: teams, score, date, and the acquired stats. */
export default function HistoryMatchRow({ match }: { match: MatchWithStats }) {
  return (
    <Link
      href={`/match/${match.id}`}
      className="card p-4 block hover:border-text-secondary/40 transition-colors"
    >
      <div className="flex items-center justify-between text-xs text-text-secondary mb-2">
        <span>{formatKickoffDate(match.kickoff)}</span>
        <span>{new Date(match.kickoff).getFullYear()}</span>
      </div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <span className="truncate text-right">{match.home_team.name}</span>
        <ScoreBig home={match.home_score} away={match.away_score} className="text-lg" />
        <span className="truncate">{match.away_team.name}</span>
      </div>
      <MatchStatsInline stats={match.stats} />
    </Link>
  );
}
