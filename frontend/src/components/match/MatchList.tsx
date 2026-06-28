import type { MatchListItem } from "@/lib/types";
import { groupByLeague } from "@/lib/utils";
import MatchCard from "@/components/match/MatchCard";
import CompetitionBadge from "@/components/ui/CompetitionBadge";

/** Matches grouped by league, each group a labelled header + grid of cards. */
export default function MatchList({
  matches,
  emptyText = "No matches.",
  grouped = true,
}: {
  matches: MatchListItem[];
  emptyText?: string;
  grouped?: boolean;
}) {
  if (matches.length === 0) {
    return (
      <div className="card p-8 text-center text-sm text-text-secondary">
        {emptyText}
      </div>
    );
  }

  if (!grouped) {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        {matches.map((m) => (
          <MatchCard key={m.id} match={m} showLeague />
        ))}
      </div>
    );
  }

  const groups = groupByLeague(matches);
  return (
    <div className="space-y-7">
      {Object.entries(groups).map(([league, group]) => (
        <div key={league}>
          <div className="mb-3 flex items-center gap-2.5">
            <CompetitionBadge name={league} className="h-6 w-6 text-[10px]" />
            <h3 className="text-sm font-semibold">{league}</h3>
            <span className="chip ml-auto px-2 py-0.5 font-mono text-[10px]">
              {group.length}
            </span>
          </div>
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
