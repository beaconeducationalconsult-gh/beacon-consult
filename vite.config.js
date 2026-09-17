import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import babel from '@rolldown/plugin-babel'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // React Compiler — see docs/conventions.md ("don't hand-memoize reflexively").
    babel({ plugins: ['babel-plugin-react-compiler'] }),
  ],
  server: {
    host: true,
    port: 5199, // matches .claude/launch.json
    // Cloud dev sandboxes proxy the dev server through a generated hostname;
    // without this Vite answers 403 "Blocked request".
    allowedHosts: ['.e2b.app', 'localhost'],
  },
  preview: {
    host: true,
    port: 4173,
    allowedHosts: ['.e2b.app', 'localhost'],
  },
})
