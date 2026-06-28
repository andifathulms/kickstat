import type { Metadata } from "next";
import { Inter, DM_Mono } from "next/font/google";
import "@/styles/globals.css";
import { getLeagues } from "@/lib/api";
import { groupLeagues } from "@/lib/competitions";
import SiteHeader from "@/components/layout/SiteHeader";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-dm-mono",
});

export const metadata: Metadata = {
  title: "Kickstat — Football Analytics",
  description:
    "Live scores, match stats, league standings, and AI predictions for Europe's top leagues and Indonesian Liga 1.",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const leagues = await getLeagues().catch(() => ({
    count: 0,
    next: null,
    previous: null,
    results: [],
  }));
  const groups = groupLeagues(leagues.results.filter((l) => l.is_active));

  return (
    <html lang="en" className={`${inter.variable} ${dmMono.variable}`}>
      <body>
        <SiteHeader groups={groups} />
        <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
        <footer className="border-t border-border/60">
          <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-8 text-xs text-text-muted sm:flex-row sm:items-center sm:justify-between">
            <span>
              <span className="font-mono text-text-secondary">kickstat</span> —
              a football analytics demo.
            </span>
            <span>
              Data from football-data.org, API-Football &amp; StatsBomb.
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
