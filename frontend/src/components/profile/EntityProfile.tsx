import Link from "next/link";
import type { MatchListItem } from "@/lib/types";
import MatchList from "@/components/match/MatchList";
import SectionHeader from "@/components/ui/SectionHeader";

export interface ProfileStat {
  label: string;
  value: string | number;
  accent?: boolean;
}

/** Shared layout for referee / stadium / coach / player profile pages. */
export default function EntityProfile({
  eyebrow,
  title,
  subtitle,
  stats,
  matches,
  matchesTitle = "Matches",
  emptyText = "No matches found.",
  crumb,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  stats?: ProfileStat[];
  matches: MatchListItem[];
  matchesTitle?: string;
  emptyText?: string;
  crumb?: { href: string; label: string };
}) {
  return (
    <div className="space-y-8">
      <nav className="flex items-center gap-2 text-xs text-text-secondary">
        <Link href="/" className="hover:text-accent">
          Home
        </Link>
        {crumb && (
          <>
            <span className="text-text-muted">/</span>
            <Link href={crumb.href} className="hover:text-accent">
              {crumb.label}
            </Link>
          </>
        )}
        <span className="text-text-muted">/</span>
        <span className="text-text-primary">{title}</span>
      </nav>

      <header className="relative overflow-hidden rounded-2xl border border-border bg-surface p-6">
        <div className="pointer-events-none absolute inset-0 bg-accent-sheen opacity-60" />
        <div className="relative">
          <span className="stat-label text-accent/90">{eyebrow}</span>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {subtitle && (
            <p className="mt-1 text-sm text-text-secondary">{subtitle}</p>
          )}
          {stats && stats.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2.5">
              {stats.map((s) => (
                <div
                  key={s.label}
                  className="flex items-center gap-2 rounded-lg border border-border bg-pitch-black/40 px-3 py-2"
                >
                  <span
                    className={`font-mono text-lg font-medium tabular-nums ${
                      s.accent ? "text-accent" : "text-text-primary"
                    }`}
                  >
                    {s.value}
                  </span>
                  <span className="stat-label">{s.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </header>

      <section>
        <SectionHeader eyebrow="Fixtures" title={matchesTitle} />
        <MatchList matches={matches} emptyText={emptyText} />
      </section>
    </div>
  );
}
