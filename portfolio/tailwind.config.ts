import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "primary": "#00ff40",
        "background-light": "#f5f8f6",
        "background-dark": "#000000",
        "terminal-gray": "#27272A",
      },
      fontFamily: {
        "display": ["var(--font-space-grotesk)", "monospace"],
      },
      borderRadius: {
        "DEFAULT": "0px",
        "sm": "0px",
        "md": "0px",
        "lg": "0px",
        "xl": "0px",
        "2xl": "0px",
        "3xl": "0px",
        "full": "0px"
      },
    }
  },
  plugins: [],
};

export default config;
