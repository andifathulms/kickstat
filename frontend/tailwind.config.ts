import type { Config } from "tailwindcss";

// Kickstat "Pitch Dark" palette — see PRD Design System. Do not hardcode hex in components.
const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "pitch-black": "#0D0F12",
        surface: "#161A1F",
        "surface-raised": "#1E232A",
        border: "#2A3038",
        "grass-green": "#00D46A",
        "amber-goal": "#FFB800",
        "red-card": "#FF3B3B",
        "text-primary": "#F0F2F5",
        "text-secondary": "#8A96A3",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-dm-mono)", "ui-monospace", "monospace"],
      },
      keyframes: {
        "live-pulse": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(0, 212, 106, 0.5)" },
          "50%": { boxShadow: "0 0 0 4px rgba(0, 212, 106, 0)" },
        },
        "dot-pulse": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        "live-pulse": "live-pulse 2s ease-in-out infinite",
        "dot-pulse": "dot-pulse 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
