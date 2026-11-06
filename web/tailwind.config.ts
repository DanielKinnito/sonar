import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sonar: {
          bg: "#0B0E14",
          panel: "#121722",
          card: "#181F2E",
          border: "#232D42",
          borderHover: "#334155",
          cyan: "#38BDF8",
          green: "#10B981",
          amber: "#F59E0B",
          red: "#EF4444",
          text: "#F1F5F9",
          secondary: "#94A3B8",
          muted: "#64748B",
        },
      },
      fontFamily: {
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          '"Liberation Mono"',
          '"Courier New"',
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};
export default config;
