import { cn } from "@/lib/utils";

type Result = "W" | "D" | "L";

const STYLES: Record<Result, string> = {
  W: "bg-grass-green/15 text-grass-green",
  D: "bg-amber-goal/15 text-amber-goal",
  L: "bg-red-card/15 text-red-card",
};

export function FormBadge({ result }: { result: Result }) {
  return (
    <span
      className={cn(
        "inline-flex h-6 w-6 items-center justify-center rounded text-xs font-bold",
        STYLES[result]
      )}
    >
      {result}
    </span>
  );
}

/** A row of last-5 form badges (oldest → newest). */
export default function FormBadges({ form }: { form: Result[] }) {
  if (form.length === 0) {
    return <span className="text-text-secondary text-xs">No recent form</span>;
  }
  return (
    <div className="flex gap-1">
      {form.map((r, i) => (
        <FormBadge key={i} result={r} />
      ))}
    </div>
  );
}
