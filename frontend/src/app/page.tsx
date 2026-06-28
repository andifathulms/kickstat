import Link from "next/link";
import {
  getLeagues,
  getLiveMatches,
  getMatchesByDate,
  getTodayPredictions,
} from "@/lib/api";
import { todayISODate } from "@/lib/utils";
import { groupLeagues } from "@/lib/competitions";
import LiveTicker from "@/components/match/LiveTicker";
import MatchList from "@/components/match/MatchList";
import PredictionCard from "@/components/match/PredictionCard";
import SectionHeader from "@/components/ui/SectionHeader";
import CompetitionBadge from "@/components/ui/CompetitionBadge";

export const revalidate = 60;

async function safe<T>(p: Promise<T>, fallback: T): Promise<T> {
  try {
    return await p;
  } catch {
    return fallback;
  }
}

const emptyPage = { count: 0, next: null, previous: null, results: [] };

export default async function HomePage() {
  const today = todayISODate();
  const [live, todayMatches, predictions, leagues] = await Promise.all([
    safe(getLiveMatches(), []),
    safe(getMatchesByDate(today), emptyPage),
    safe(getTodayPredictions(), []),
    safe(getLeagues(), emptyPage),
  ]);

  const fixtures = todayMatches.results.filter((m) => m.status === "SCHEDULED");
  const results = todayMatches.results.filter((m) => m.status === "FINISHED");
  const topPredictions = predictions.slice(0, 3);
  const groups = groupLeagues(leagues.results.filter((l) => l.is_active));

  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl border border-border bg-surface p-7 sm:p-10">
        <div className="pointer-events-none absolute inset-0 bg-accent-sheen" />
        <div className="relative">
          <span className="stat-label text-accent/90">
            Live scores · Stats · AI predictions
          </span>
          <h1 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
            Football, decoded.
          </h1>
          <p className="mt-3 max-w-xl text-sm text-text-secondary sm:text-base">
            Real-time scores, deep match stats and model-driven predictions
            across Europe&apos;s top leagues and Indonesian Liga 1 — organised by
            competition and season.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3 text-xs">
            <Stat value={leagues.count} label="Competitions" />
            <Stat value={fixtures.length + results.length} label="Today" />
            <Stat value={live.length} label="Live now" accent={live.length > 0} />
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link href="/standings" className="btn-accent">
              Browse competitions
            </Link>
            <Link
              href="/predictions"
              className="inline-flex items-center rounded-lg border border-border-strong px-4 py-2 text-sm text-text-secondary transition-colors hover:text-text-primary"
            >
              Today&apos;s AI picks
            </Link>
          </div>
        </div>
      </section>

      {/* Live ticker */}
      <section className="-mt-4">
        <LiveTicker initial={live} />
      </section>

      {/* Today's fixtures */}
      <section>
        <SectionHeader
          eyebrow="Matchday"
          title="Today's fixtures"
          href="/standings"
          hrefLabel="All competitions"
        />
        <MatchList
          matches={fixtures}
          emptyText="No fixtures scheduled for today."
        />
      </section>

      {/* Top predictions */}
      {topPredictions.length > 0 && (
        <section>
          <SectionHeader
            eyebrow="Model"
            title="Top AI predictions"
            href="/predictions"
          />
          <div className="grid gap-3 sm:grid-cols-3">
            {topPredictions.map((p) => (
              <PredictionCard key={p.id} prediction={p} />
            ))}
          </div>
        </section>
      )}

      {/* Recent results */}
      <section>
        <SectionHeader eyebrow="Full time" title="Recent results" />
        <MatchList matches={results} emptyText="No results yet today." />
      </section>

      {/* Browse competitions */}
      <section>
        <SectionHeader
          eyebrow="Explore"
          title="Browse competitions"
          href="/standings"
        />
        <div className="space-y-6">
          {groups.map((g) => (
            <div key={g.meta.id}>
              <div className="mb-2 flex items-baseline gap-2">
                <h3 className="text-sm font-semibold">{g.meta.label}</h3>
                <span className="text-xs text-text-muted">{g.meta.blurb}</span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {g.leagues.map((l) => (
                  <Link
                    key={l.id}
                    href={`/league/${l.slug}`}
                    className="card card-hover flex items-center gap-3 p-3"
                  >
                    <CompetitionBadge name={l.name} />
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {l.name}
                      </div>
                      <div className="truncate text-xs text-text-secondary">
                        {l.country}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Stat({
  value,
  label,
  accent = false,
}: {
  value: number;
  label: string;
  accent?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-pitch-black/40 px-3 py-2">
      <span
        className={`font-mono text-lg font-medium tabular-nums ${
          accent ? "text-grass-green" : "text-text-primary"
        }`}
      >
        {value}
      </span>
      <span className="stat-label">{label}</span>
    </div>
  );
}
