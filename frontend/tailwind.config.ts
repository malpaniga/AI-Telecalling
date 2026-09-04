import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Groq-inspired dark palette
        ink: "#08080a", // page background
        panel: "#121215", // cards / panels
        "panel-2": "#17171b", // nested surfaces
        line: "#26262c", // borders
        "line-strong": "#34343c", // hover / emphasized borders
        fg: "#ededf0", // primary text
        muted: "#8a8a92", // secondary text
        faint: "#5c5c64", // tertiary text
        accent: "#F55036", // Groq coral/orange
        "accent-dim": "#7a2c1f",
        good: "#3fb950",
        warn: "#d29922",
        bad: "#f85149",
      },
      borderRadius: {
        // Sharp edges: keep radii tiny and crisp.
        none: "0px",
        sm: "2px",
        DEFAULT: "3px",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
