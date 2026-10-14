/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: { 950: "#0D1B33", 900: "#142A4D", 800: "#1D3A66" },
        canvas: "#F5F7FB",
        surface: "#FFFFFF",
        line: "#E3E7EF",
        brand: { DEFAULT: "#2F6FED", soft: "#EAF0FE" },
        danger: { DEFAULT: "#D64545", soft: "#FBEAEA" },
        warning: { DEFAULT: "#E8A33D", soft: "#FDF3E3" },
        success: { DEFAULT: "#2FA36B", soft: "#E9F6EF" },
        ink: { primary: "#101828", secondary: "#5B6472", inverse: "#E8EDF7" },
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        sans: ["Inter", "sans-serif"],
      },
      borderRadius: {
        xl: "14px",
      },
    },
  },
  plugins: [],
};