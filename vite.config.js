import { execSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import babel from '@rolldown/plugin-babel'
import { resolveFirebaseConfig } from './src/lib/firebaseConfigSource.js'
import { firebaseConfig as committedFirebaseConfig } from './src/firebaseConfig.js'

/*
 * P0-1: Vite embeds the Firebase config at build time, so a build with empty
 * values is green and the deployed app shows the setup notice — a blank app that
 * nothing in the pipeline mentions. Two changes fix that:
 *
 *  1. the log lines below, printed where whoever deployed will see them;
 *  2. `dist/build-info.json`, served from the deploy, so "did the production
 *     environment get the six values" is answerable with one request instead of
 *     a browser console — `make verify-deploy URL=https://…`.
 *
 * Both report what the *bundle* will carry, which is not simply what the
 * environment holds: `src/firebase.js` falls back to the committed
 * `src/firebaseConfig.js` for anything blank or absent. So a variable that
 * exists in Vercel but is empty is reported by name — it used to empty out a
 * committed value and turn a green build into a setup notice with nothing to
 * see — and a build whose values came from the repository says so.
 */
function firebaseConfigGuard(env, command) {
  const resolved = resolveFirebaseConfig({ env, committed: committedFirebaseConfig })
  const { missing } = resolved
  const info = {
    firebaseConfigured: missing.length === 0,
    missingEnv: missing,
    configSource: resolved.source,
    projectId: resolved.config.projectId || null,
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
      const line = '─'.repeat(72)
      if (command === 'build' && resolved.envBlankNames.length) {
        console.warn(`\n${line}
  These build-environment variables are set but EMPTY: ${resolved.envBlankNames.join(', ')}
  Blank wins over both .env files and the committed config in Vite's loader, so
  whoever set them has emptied out a value the repository supplies. Give them a
  value in Vercel → Settings → Environment Variables, or delete them.
  The build below uses the committed value from src/firebaseConfig.js.
${line}\n`)
      }
      if (command === 'build' && missing.length) {
        console.warn(`\n${line}
  Building WITHOUT Firebase config: ${missing.join(', ')}
  The deployed app will show the setup notice, not the portal.
  Set all six VITE_FIREBASE_* values in Vercel → Settings → Environment
  Variables, for BOTH Production and Preview, then redeploy, or fill them into
  src/firebaseConfig.js (the committed config every build can read).
  See docs/build-deploy.md.
${line}\n`)
      } else if (command === 'build') {
        console.log(`Firebase config: all six values present (source: ${resolved.source}).`)
      }
    },
    generateBundle() {
      // The curriculum build writes the bundle hash the service worker names its
      // cache after; carrying it into build-info.json is what lets
      // `make verify-deploy` say whether a deploy is serving this bundle.
      //
      // Read it with fs, not `execSync('cat …')`: `cat` is not a Windows
      // program, so on the machine that actually deploys every build reported
      // `bundleHash: null` and the one check that compares a deploy against this
      // checkout silently had nothing to compare.
      try {
        const report = JSON.parse(readFileSync(resolve(process.cwd(), 'public/curriculum/_BUILD_REPORT.json'), 'utf8'))
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
