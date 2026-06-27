import { cn } from "@/lib/utils";

export default function StatLabel({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <span className={cn("stat-label", className)}>{children}</span>;
}
