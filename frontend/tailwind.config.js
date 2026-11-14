/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--bg) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        surface2: "rgb(var(--surface2) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)",
        ink: "rgb(var(--ink) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        brand: "rgb(var(--brand) / <alpha-value>)",
        brandsoft: "rgb(var(--brandsoft) / <alpha-value>)",
        okbg: "rgb(var(--okbg) / <alpha-value>)",
        ok: "rgb(var(--ok) / <alpha-value>)",
        bad: "rgb(var(--bad) / <alpha-value>)",
        badbg: "rgb(var(--badbg) / <alpha-value>)",
        warn: "rgb(var(--warn) / <alpha-value>)",
        warnbg: "rgb(var(--warnbg) / <alpha-value>)",
        peach: "rgb(var(--peach) / <alpha-value>)",
      },
      fontFamily: {
        sans: ['"Nunito Sans"', "system-ui", "sans-serif"],
        hand: ["Caveat", "cursive"],
      },
      borderRadius: { card: "18px" },
      boxShadow: {
        card: "0 1px 2px rgb(60 40 20 / 0.04), 0 6px 18px -6px rgb(60 40 20 / 0.08)",
      },
    },
  },
  plugins: [],
};
