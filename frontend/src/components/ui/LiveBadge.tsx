export default function LiveBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 text-grass-green">
      <span className="h-2 w-2 rounded-full bg-grass-green animate-dot-pulse" />
      <span className="text-[11px] font-semibold uppercase tracking-widest">
        Live
      </span>
    </span>
  );
}
