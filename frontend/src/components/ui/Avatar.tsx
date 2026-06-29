import { cn } from "@/lib/utils";

// Deterministic, on-brand tint per name so monograms aren't all identical.
const TINTS = [
  "bg-grass-green/15 text-grass-green",
  "bg-amber-goal/15 text-amber-goal",
  "bg-accent/15 text-accent",
  "bg-red-card/15 text-red-card",
  "bg-text-secondary/15 text-text-secondary",
];

function initials(name: string): string {
  const words = name.replace(/[^a-zA-Z0-9 ]/g, "").split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}

function tintFor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return TINTS[h % TINTS.length];
}

/**
 * Round avatar: shows an image (team crest) when `src` is given, otherwise a
 * deterministic colored monogram. We have no player/coach photos in the data,
 * so people fall back to monograms.
 */
export default function Avatar({
  name,
  src,
  className,
  contain = false,
}: {
  name: string;
  src?: string | null;
  className?: string;
  contain?: boolean;
}) {
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt=""
        className={cn(
          "shrink-0 rounded-full bg-surface-raised",
          contain ? "object-contain p-1" : "object-cover",
          className
        )}
      />
    );
  }
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold",
        tintFor(name),
        className
      )}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}
