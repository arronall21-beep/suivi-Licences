/** @type {import('tailwindcss').Config} */
// Les couleurs viennent des variables CSS de src/theme/tokens.css (charte centralisée).
const scale = (name, steps) =>
  Object.fromEntries(steps.map((s) => [s, `rgb(var(--${name}-${s}) / <alpha-value>)`]));

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["var(--font-sans)"] },
      colors: {
        brand: scale("brand", [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]),
        accent: scale("accent", [100, 400, 500, 600]),
        danger: scale("danger", [50, 100, 200, 500, 600, 700, 800]),
        caution: scale("caution", [50, 100, 200, 500, 600, 700, 800]),
        warning: scale("warning", [50, 100, 200, 500, 600, 700, 800]),
        success: scale("success", [50, 100, 200, 500, 600, 700, 800]),
      },
    },
  },
  plugins: [],
};
