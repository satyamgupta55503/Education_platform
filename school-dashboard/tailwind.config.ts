// tailwind.config.ts
import type { Config } from "tailwindcss";
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
        mono: ["DM Mono", "monospace"],
      },
      colors: {
        brand: { 50: "#EFF6FF", 500: "#3B82F6", 900: "#0F1729" },
      },
      borderRadius: { "2xl": "16px", "3xl": "20px" },
    },
  },
  plugins: [],
};
export default config;
