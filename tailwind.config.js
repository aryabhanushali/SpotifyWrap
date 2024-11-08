/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./wrapped/templates/**/*.html",  // your template files
    "./templates/**/*.html",          // any project-level templates
  ],
  theme: {
    extend: {
      colors: {
        'spotify-black': '#191414',
        'spotify-dark': '#121212',
        'spotify-dark-card': '#282828',
        'spotify-hover': '#3E3E3E',
        'spotify-green': '#1DB954',
        'spotify-green-dark': '#1aa34a',
      },
    },
  },
  plugins: [],
}