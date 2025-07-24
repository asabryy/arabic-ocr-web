// tailwind.config.js
import forms from '@tailwindcss/forms';
import typography from '@tailwindcss/typography';

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#4b8782", // green-700
          light: "#22c55e",   // green-500
          dark: "#166534",    // green-800
        },
        accent: "#f3e8d2",     // orange-500 for highlights
        background: "#fefcf9"  // light neutral background
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"]
      },
      container: {
        center: true,
        padding: "1rem",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem"
      },
    },
  },
  plugins: [forms, typography],
}
