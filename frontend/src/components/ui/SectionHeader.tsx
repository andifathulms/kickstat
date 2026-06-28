import Link from "next/link";

/** Consistent section heading: small eyebrow rule + title + optional link. */
export default function SectionHeader({
  title,
  eyebrow,
  href,
  hrefLabel = "View all",
  children,
}: {
  title: string;
  eyebrow?: string;
  href?: string;
  hrefLabel?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <div className="mb-1 flex items-center gap-2">
            <span className="h-3 w-1 rounded-full bg-accent" />
            <span className="stat-label text-accent/90">{eyebrow}</span>
          </div>
        )}
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      </div>
      {children}
      {href && (
        <Link
          href={href}
          className="shrink-0 text-sm text-text-secondary transition-colors hover:text-accent"
        >
          {hrefLabel} →
        </Link>
      )}
    </div>
  );
}
