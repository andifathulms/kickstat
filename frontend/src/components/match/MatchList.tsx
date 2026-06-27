import type { MatchListItem } from "@/lib/types";
import { groupByLeague } from "@/lib/utils";
import MatchCard from "@/components/match/MatchCard";
import StatLabel from "@/components/ui/StatLabel";

/** Matches grouped by league, each group a small heading + grid of cards. */
export default function MatchList({
  matches,
  emptyText = "No matches.",
}: {
  matches: MatchListItem[];
  emptyText?: string;
}) {
  if (matches.length === 0) {
    return <p className="text-text-secondary text-sm">{emptyText}</p>;
  }
  const grouped = groupByLeague(matches);
  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([league, group]) => (
        <div key={league}>
          <StatLabel className="block mb-2">{league}</StatLabel>
          <div className="grid gap-3 sm:grid-cols-2">
            {group.map((m) => (
              <MatchCard key={m.id} match={m} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
