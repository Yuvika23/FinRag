import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#090d16",
        foreground: "#f8fafc",
        card: "#0f172a",
        cardForeground: "#f1f5f9",
        border: "#1e293b",
        primary: {
          DEFAULT: "#10b981",
          hover: "#059669",
          muted: "#064e3b",
        },
        navy: {
          800: "#1e293b",
          850: "#131b2e",
          900: "#0b1120",
          950: "#070a12",
        },
        accent: {
          blue: "#3b82f6",
          purple: "#8b5cf6",
          emerald: "#10b981",
          amber: "#f59e0b",
          rose: "#f43f5e",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
