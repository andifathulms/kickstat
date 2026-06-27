import Link from "next/link";
import {
  getLeagues,
  getLiveMatches,
  getMatchesByDate,
  getTodayPredictions,
} from "@/lib/api";
import { todayISODate } from "@/lib/utils";
import LiveTicker from "@/components/match/LiveTicker";
import MatchList from "@/components/match/MatchList";
import PredictionCard from "@/components/match/PredictionCard";

export const revalidate = 60;

async function safe<T>(p: Promise<T>, fallback: T): Promise<T> {
  try {
    return await p;
  } catch {
    return fallback;
  }
}

export default async function HomePage() {
  const today = todayISODate();
  const [live, todayMatches, predictions, leagues] = await Promise.all([
    safe(getLiveMatches(), []),
    safe(getMatchesByDate(today), { count: 0, next: null, previous: null, results: [] }),
    safe(getTodayPredictions(), []),
    safe(getLeagues(), { count: 0, next: null, previous: null, results: [] }),
  ]);

  const fixtures = todayMatches.results.filter((m) => m.status === "SCHEDULED");
  const results = todayMatches.results.filter((m) => m.status === "FINISHED");
  const topPredictions = predictions.slice(0, 3);

  return (
    <div className="space-y-10">
      {/* Hero: live ticker */}
      <section>
        <LiveTicker initial={live} />
      </section>

      {/* Today's fixtures */}
      <Section title="Today's fixtures">
        <MatchList matches={fixtures} emptyText="No fixtures scheduled for today." />
      </Section>

      {/* Top predictions */}
      {topPredictions.length > 0 && (
        <Section title="Top AI predictions" href="/predictions">
          <div className="grid gap-3 sm:grid-cols-3">
            {topPredictions.map((p) => (
              <PredictionCard key={p.id} prediction={p} />
            ))}
          </div>
        </Section>
      )}

      {/* Recent results */}
      <Section title="Recent results">
        <MatchList matches={results} emptyText="No results yet today." />
      </Section>

      {/* Leagues */}
      <Section title="Leagues" href="/standings">
        <div className="flex flex-wrap gap-2">
          {leagues.results.map((l) => (
            <Link
              key={l.id}
              href={`/league/${l.slug}`}
              className="rounded-lg bg-surface-raised px-3 py-1.5 text-sm hover:text-grass-green"
            >
              {l.name}
            </Link>
          ))}
        </div>
      </Section>
    </div>
  );
}

function Section({
  title,
  href,
  children,
}: {
  title: string;
  href?: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">{title}</h2>
        {href && (
          <Link href={href} className="text-sm text-text-secondary hover:text-grass-green">
            View all →
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}
