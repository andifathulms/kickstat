export default function LiveBadge({ minute }: { minute?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-grass-green/10 px-2 py-0.5 text-grass-green">
      <span className="h-1.5 w-1.5 rounded-full bg-grass-green animate-dot-pulse" />
      <span className="text-[10px] font-semibold uppercase tracking-[0.14em]">
        {minute ? minute : "Live"}
      </span>
    </span>
  );
}
