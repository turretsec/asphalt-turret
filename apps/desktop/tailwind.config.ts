/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
    theme: {
    borderRadius: {
      sm: '4px',
      md: '6px',
      lg: '8px'
    }
  }
  },
  plugins: [
    require('tailwind-scrollbar')({ nocompatible: true }),
  ],
}