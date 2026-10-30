/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: '#121212',
        'ink-soft': '#6B6862',
        paper: '#F2F0EC',
        'paper-dim': '#E7E3DA',
        line: '#D9D5CC',
        signal: '#FF3B24',
        'signal-dim': '#E6330F',
      },
      fontFamily: {
        display: ['"Oswald"', 'sans-serif'],
        body: ['"Inter"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      letterSpacing: {
        widest2: '0.2em',
      },
    },
  },
  plugins: [],
}
