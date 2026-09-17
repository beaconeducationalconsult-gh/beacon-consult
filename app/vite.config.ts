import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  // Cloud dev sandboxes (and anyone proxying the dev server through a
  // generated hostname) need their host allowed, otherwise Vite answers
  // 403 "Blocked request" and the app never loads. `.e2b.app` covers the
  // preview proxy; localhost covers normal local work.
  server: {
    allowedHosts: ['.e2b.app', 'localhost'],
  },
  preview: {
    allowedHosts: ['.e2b.app', 'localhost'],
  },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            // Cache all static curriculum JSON
            urlPattern: /\/curriculum\/.+\.json$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'curriculum-cache',
              expiration: {
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
              },
            },
          },
        ],
      },
      manifest: {
        name: 'Beacon Consult — Teaching Materials',
        short_name: 'Beacon',
        theme_color: '#1e40af',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
    }),
  ],
})
