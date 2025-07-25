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
          DEFAULT: "#f24901", // green-700
          light: "#e8deceff",   // green-500
          dark: "#ff9933ff",    // green-800
        },
        accent: "#f3e8d2",     // orange-500 for highlights
        background: "#fbf9f9"  // light neutral background
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
