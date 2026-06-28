import type { Config } from "tailwindcss";

// Kickstat "Midnight Pitch" palette — see tokens.css. Do not hardcode hex in components.
const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "pitch-black": "#0B0E14",
        surface: "#121722",
        "surface-raised": "#1A2130",
        border: "#232C3B",
        "border-strong": "#303B4D",
        accent: "#C6FF3D",
        "accent-ink": "#0B1402",
        "grass-green": "#34D399",
        "amber-goal": "#FBBF24",
        "red-card": "#F87171",
        "text-primary": "#E7ECF3",
        "text-secondary": "#8A95A8",
        "text-muted": "#5C6678",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-dm-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(198,255,61,0.25), 0 0 24px -6px rgba(198,255,61,0.35)",
        "glow-green":
          "0 0 0 1px rgba(52,211,153,0.25), 0 0 22px -8px rgba(52,211,153,0.4)",
        panel: "0 1px 0 0 rgba(255,255,255,0.02), 0 8px 30px -12px rgba(0,0,0,0.6)",
      },
      backgroundImage: {
        "accent-sheen":
          "linear-gradient(135deg, rgba(198,255,61,0.16), rgba(198,255,61,0))",
        "pitch-radial":
          "radial-gradient(1200px 600px at 70% -10%, rgba(198,255,61,0.06), transparent 60%), radial-gradient(900px 500px at 10% 0%, rgba(52,211,153,0.05), transparent 55%)",
      },
      keyframes: {
        "live-pulse": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(52, 211, 153, 0.45)" },
          "50%": { boxShadow: "0 0 0 5px rgba(52, 211, 153, 0)" },
        },
        "dot-pulse": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
      animation: {
        "live-pulse": "live-pulse 2s ease-in-out infinite",
        "dot-pulse": "dot-pulse 1.2s ease-in-out infinite",
        "fade-up": "fade-up 0.4s ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
