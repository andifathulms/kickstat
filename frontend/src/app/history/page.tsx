import Link from "next/link";
import type { Metadata } from "next";
import { getArchiveLeagues } from "@/lib/api";
import StatLabel from "@/components/ui/StatLabel";

export const revalidate = 600;

export const metadata: Metadata = {
  title: "History — Kickstat",
  description:
    "Browse the historical match archive with per-match stats across leagues and seasons.",
};

export default async function HistoryPage() {
  const leagues = await getArchiveLeagues().catch(() => []);
  const total = leagues.reduce((n, l) => n + l.match_count, 0);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Match archive</h1>
        <p className="text-text-secondary text-sm">
          {total.toLocaleString()} historical matches with stats across{" "}
          {leagues.length} competitions.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {leagues.map((l) => (
          <Link
            key={l.id}
            href={`/history/${l.slug}`}
            className="card p-4 block hover:border-text-secondary/40 transition-colors"
          >
            <div className="font-medium truncate">{l.name}</div>
            <div className="text-xs text-text-secondary mt-0.5">{l.country}</div>
            <div className="flex items-center justify-between mt-3">
              <StatLabel>{l.match_count.toLocaleString()} matches</StatLabel>
              {l.first_year && l.last_year && (
                <span className="text-xs text-text-secondary font-mono">
                  {l.first_year === l.last_year
                    ? l.first_year
                    : `${l.first_year}–${l.last_year}`}
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
