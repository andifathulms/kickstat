// Deterministic per-team accent colour. We have no real kit colours in the
// data, so this derives a stable, distinct hue from the team name to give each
// team page a bit of identity.
export function teamAccent(name: string): {
  color: string;
  soft: string;
  gradient: string;
} {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  const hue = h % 360;
  return {
    color: `hsl(${hue} 72% 62%)`,
    soft: `hsl(${hue} 72% 55% / 0.16)`,
    gradient: `linear-gradient(135deg, hsl(${hue} 72% 55% / 0.22), transparent 60%)`,
  };
}
