module.exports = {
  content: [
    "./wrapped/templates/**/*.html",  //  My template files
    "./templates/**/*.html",          //  project-level templates
  ],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        // Dark mode colors
        'spotify-black': '#191414',
        'spotify-dark': '#121212',
        'spotify-dark-card': '#282828',
        'spotify-hover': '#3E3E3E',
        'spotify-green': '#1DB954',
        'spotify-green-dark': '#1aa34a',

        // Light mode colors
        'spotify-light': {
          'bg': '#ffffff',
          'card': '#f7f7f7',
          'hover': '#efefef',
          'text': '#121212',
          'text-secondary': '#6b7280',
        },
      },
    },
  },
  plugins: [],
}