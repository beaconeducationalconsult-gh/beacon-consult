import { execSync } from 'node:child_process'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import babel from '@rolldown/plugin-babel'

/** The six values src/firebase.js reads, in the order .env.example lists them. */
const FIREBASE_KEYS = [
  'VITE_FIREBASE_API_KEY',
  'VITE_FIREBASE_AUTH_DOMAIN',
  'VITE_FIREBASE_PROJECT_ID',
  'VITE_FIREBASE_STORAGE_BUCKET',
  'VITE_FIREBASE_MESSAGING_SENDER_ID',
  'VITE_FIREBASE_APP_ID',
]

/*
 * P0-1: Vite embeds the Firebase config at build time, so a build with empty
 * values is green and the deployed app shows the setup notice — a blank app that
 * nothing in the pipeline mentions. Two changes fix that:
 *
 *  1. the warning below, printed where whoever deployed will see it;
 *  2. `dist/build-info.json`, served from the deploy, so "did the production
 *     environment get the six values" is answerable with one request instead of
 *     a browser console — `make verify-deploy URL=https://…`.
 */
function firebaseConfigGuard(env, command) {
  const missing = FIREBASE_KEYS.filter((key) => !env[key])
  const info = {
    firebaseConfigured: missing.length === 0,
    missingEnv: missing,
    projectId: env.VITE_FIREBASE_PROJECT_ID || null,
    bundleHash: null,
    commit: null,
    builtAt: new Date().toISOString(),
  }

  return {
    name: 'beacon-build-info',
    apply: 'build',
    configResolved() {
      try {
        info.commit = execSync('git rev-parse --short HEAD', { stdio: ['ignore', 'pipe', 'ignore'] })
          .toString().trim()
      } catch {
        info.commit = null // no git (a tarball deploy) — not worth failing over
      }
      if (command === 'build' && missing.length) {
        const line = '─'.repeat(72)
        console.warn(`\n${line}
  Building WITHOUT Firebase config: ${missing.join(', ')}
  The deployed app will show the setup notice, not the portal.
  Set all six VITE_FIREBASE_* values in Vercel → Settings → Environment
  Variables, for BOTH Production and Preview, then redeploy. Locally: copy
  .env.example to .env.local. See docs/build-deploy.md.
${line}\n`)
      }
    },
    generateBundle() {
      // The curriculum build writes the bundle hash the service worker names its
      // cache after; carrying it into build-info.json is what lets
      // `make verify-deploy` say whether a deploy is serving this bundle.
      try {
        const report = JSON.parse(
          execSync('cat public/curriculum/_BUILD_REPORT.json', { stdio: ['ignore', 'pipe', 'ignore'] })
            .toString(),
        )
        info.bundleHash = report.bundleHash || null
      } catch {
        info.bundleHash = null
      }
      this.emitFile({
        type: 'asset',
        fileName: 'build-info.json',
        source: `${JSON.stringify(info, null, 2)}\n`,
      })
    },
  }
}

export default defineConfig(({ command, mode }) => {
  // Third argument '' loads every var in .env*, not just the ones Vite prefixes
  // by default — the app's config is VITE_FIREBASE_*, and the guard needs to see
  // what the build will actually embed.
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      react(),
      tailwindcss(),
      // React Compiler — see docs/conventions.md ("don't hand-memoize reflexively").
      babel({ plugins: ['babel-plugin-react-compiler'] }),
      firebaseConfigGuard(env, command),
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
  }
})
