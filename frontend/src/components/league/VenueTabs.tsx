import Link from "next/link";
import { VENUES, type Venue } from "@/lib/competitions";
import { cn } from "@/lib/utils";

/** Overall / Home / Away switch for a competition's standings (link-based). */
export default function VenueTabs({
  active,
  slug,
  season,
}: {
  active: Venue;
  slug: string;
  season: string;
}) {
  const href = (v: Venue) => {
    const q = new URLSearchParams({ season });
    if (v !== "overall") q.set("venue", v);
    return `/league/${slug}?${q.toString()}`;
  };
  return (
    <div className="inline-flex rounded-full border border-border bg-surface-raised p-0.5">
      {VENUES.map((v) => (
        <Link
          key={v.value}
          href={href(v.value)}
          scroll={false}
          className={cn(
            "rounded-full px-3 py-1 text-xs font-medium transition-colors",
            v.value === active
              ? "bg-accent text-accent-ink"
              : "text-text-secondary hover:text-text-primary"
          )}
        >
          {v.label}
        </Link>
      ))}
    </div>
  );
}
