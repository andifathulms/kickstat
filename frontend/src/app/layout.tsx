import type { Metadata } from "next";
import { Inter, DM_Mono } from "next/font/google";
import Link from "next/link";
import "@/styles/globals.css";

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

const NAV = [
  { href: "/", label: "Home" },
  { href: "/standings", label: "Standings" },
  { href: "/predictions", label: "Predictions" },
  { href: "/history", label: "History" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${dmMono.variable}`}>
      <body>
        <header className="border-b border-border bg-surface/80 backdrop-blur sticky top-0 z-50">
          <div className="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-grass-green" />
              <span className="font-mono text-lg font-medium tracking-tight">
                kickstat
              </span>
            </Link>
            <nav className="flex items-center gap-6 text-sm text-text-secondary">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="hover:text-text-primary transition-colors"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 py-10 text-xs text-text-secondary">
          Data from football-data.org, API-Football & StatsBomb. Kickstat is a
          demo analytics project.
        </footer>
      </body>
    </html>
  );
}
