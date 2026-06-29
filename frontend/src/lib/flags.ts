// Country (as stored on League/Team) → flagcdn code. Home-nations and
// supranational competitions get their proper flags; unknowns fall back to a
// monogram badge in the UI.
const FLAG_CODES: Record<string, string> = {
  england: "gb-eng",
  scotland: "gb-sct",
  wales: "gb-wls",
  "northern ireland": "gb-nir",
  spain: "es",
  italy: "it",
  germany: "de",
  france: "fr",
  netherlands: "nl",
  portugal: "pt",
  brazil: "br",
  indonesia: "id",
  turkey: "tr",
  "türkiye": "tr",
  greece: "gr",
  belgium: "be",
  argentina: "ar",
  "united states": "us",
  usa: "us",
  india: "in",
  europe: "eu",
};

/** flagcdn SVG URL for a country name, or null when there's no sensible flag. */
export function flagUrl(country: string | null | undefined): string | null {
  if (!country) return null;
  const code = FLAG_CODES[country.trim().toLowerCase()];
  return code ? `https://flagcdn.com/${code}.svg` : null;
}
