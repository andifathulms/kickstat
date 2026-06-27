import Link from "next/link";
import { notFound } from "next/navigation";
import { getArchiveLeagues, getHistoryMatches } from "@/lib/api";
import { cn } from "@/lib/utils";
import HistoryMatchRow from "@/components/match/HistoryMatchRow";

export const revalidate = 600;

const PAGE_SIZE = 20;

export default async function HistoryLeaguePage({
  params,
  searchParams,
}: {
  params: { slug: string };
  searchParams: { page?: string; season?: string };
}) {
  const leagues = await getArchiveLeagues().catch(() => []);
  const league = leagues.find((l) => l.slug === params.slug);
  if (!league) notFound();

  const page = Math.max(1, Number(searchParams.page) || 1);
  const season = searchParams.season ? Number(searchParams.season) : null;
  const dateRange = season
    ? { dateFrom: `${season}-07-01`, dateTo: `${season + 1}-06-30` }
    : {};

  const data = await getHistoryMatches({
    league: league.id,
    page,
    ...dateRange,
  }).catch(() => ({ count: 0, next: null, previous: null, results: [] }));

  const totalPages = Math.max(1, Math.ceil(data.count / PAGE_SIZE));

  // Season chips (newest first) from the league's year span.
  const years: number[] = [];
  if (league.first_year && league.last_year) {
    for (let y = league.last_year; y >= league.first_year; y--) years.push(y);
  }

  const href = (next: { page?: number; season?: number | null }) => {
    const q = new URLSearchParams();
    const s = next.season === undefined ? season : next.season;
    if (s) q.set("season", String(s));
    const p = next.page ?? 1;
    if (p > 1) q.set("page", String(p));
    const qs = q.toString();
    return `/history/${params.slug}${qs ? `?${qs}` : ""}`;
  };

  return (
    <div className="space-y-5">
      <header>
        <Link href="/history" className="text-sm text-text-secondary hover:text-grass-green">
          ← Archive
        </Link>
        <h1 className="text-2xl font-semibold mt-1">{league.name}</h1>
        <p className="text-text-secondary text-sm">
          {league.country} · {data.count.toLocaleString()} matches
          {season ? ` · ${season}/${(season + 1).toString().slice(2)}` : ""}
        </p>
      </header>

      {/* Season filter */}
      {years.length > 0 && (
        <div className="flex gap-1 overflow-x-auto pb-1">
          <Chip href={href({ season: null, page: 1 })} active={!season}>
            All
          </Chip>
          {years.map((y) => (
            <Chip key={y} href={href({ season: y, page: 1 })} active={season === y}>
              {`${y}/${(y + 1).toString().slice(2)}`}
            </Chip>
          ))}
        </div>
      )}

      {data.results.length === 0 ? (
        <p className="text-text-secondary text-sm">No matches for this selection.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {data.results.map((m) => (
            <HistoryMatchRow key={m.id} match={m} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <PageLink href={href({ page: page - 1 })} disabled={page <= 1}>
            ← Prev
          </PageLink>
          <span className="text-sm text-text-secondary font-mono">
            Page {page} of {totalPages}
          </span>
          <PageLink href={href({ page: page + 1 })} disabled={page >= totalPages}>
            Next →
          </PageLink>
        </div>
      )}
    </div>
  );
}

function Chip({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-colors",
        active
          ? "bg-surface-raised text-text-primary"
          : "text-text-secondary hover:text-text-primary"
      )}
    >
      {children}
    </Link>
  );
}

function PageLink({
  href,
  disabled,
  children,
}: {
  href: string;
  disabled: boolean;
  children: React.ReactNode;
}) {
  if (disabled) {
    return <span className="text-sm text-text-secondary/40">{children}</span>;
  }
  return (
    <Link href={href} className="text-sm text-text-primary hover:text-grass-green">
      {children}
    </Link>
  );
}
