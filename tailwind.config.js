/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/**/*.js"
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        "primary": "var(--accent)",
        "background": "var(--bg-main)",
        "surface": "var(--surface)",
        "surface-alt": "var(--surface-alt)",
        "surface-inset": "var(--surface-inset)",
        "text-main": "var(--text-main)",
        "text-muted": "var(--text-muted)",
        "accent-cyan": "var(--accent-secondary)",
      },
      fontFamily: {
        "display": ["Space Grotesk", "sans-serif"],
        "mono": ["Space Mono", "monospace"],
      },
      boxShadow: {
        "raised": "0 4px 6px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08)",
        "pressed": "inset 0 2px 4px rgba(0,0,0,0.6)",
        "input": "inset 0 2px 4px rgba(0,0,0,0.4), inset 0 0 0 1px rgba(255,255,255,0.05)",
      },
      borderRadius: {
        "DEFAULT": "0.125rem",
        "sm": "0.125rem",
        "md": "0.25rem",
        "lg": "0.25rem",
        "xl": "0.25rem",
        "full": "0.25rem"
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries')
  ],
}
