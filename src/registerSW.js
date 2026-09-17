// Registers the service worker in production builds only, so Vite HMR is
// untouched in dev. PWA/offline behaviour therefore only exists in
// `yarn build && yarn preview`. See docs/pwa-offline.md.
export function registerServiceWorker() {
  if (!import.meta.env.PROD) return
  if (!('serviceWorker' in navigator)) return

  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((error) => {
      console.warn('[beacon] service worker registration failed:', error)
    })
  })
}
