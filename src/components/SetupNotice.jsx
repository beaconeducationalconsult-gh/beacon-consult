/**
 * Shown instead of the app when the six VITE_FIREBASE_* values are missing.
 *
 * Before this screen existed, a missing config threw `auth/invalid-api-key`
 * while the entry module was evaluating, so the page stayed blank and nothing
 * said why. The curriculum data is static JSON in `public/curriculum/` and is
 * already present — it is Firebase, not the data, that is missing here.
 */
export default function SetupNotice() {
  return (
    <div className="min-h-screen bg-cream px-4 py-12">
      <div className="mx-auto max-w-2xl">
        <p className="section-heading">Beacon Consult</p>
        <h1 className="page-title mt-2">Firebase configuration is missing</h1>
        <p className="page-subtitle mt-2">
          The app can read the NaCCA curriculum offline, but signing in and saving work go
          through Firebase. Vite embeds the <code className="font-mono text-xs">VITE_FIREBASE_*</code>{' '}
          values at build time, and none were found — so this build has no project to talk to.
        </p>

        <div className="card mt-6 p-5">
          <h2 className="card-title">Add the six values</h2>
          <ol className="mt-3 space-y-3 text-sm text-slate-700">
            <li>
              <span className="font-semibold">1.</span> Copy the example file:
              <pre className="mt-1 overflow-x-auto rounded-md bg-slate-900 px-3 py-2 font-mono text-xs text-slate-100">
                cp .env.example .env.local
              </pre>
            </li>
            <li>
              <span className="font-semibold">2.</span> Paste the values from the Firebase
              console → <em>Project settings</em> → <em>Your apps</em> → Web app:
              <pre className="mt-1 overflow-x-auto rounded-md bg-slate-900 px-3 py-2 font-mono text-xs text-slate-100">
                {'VITE_FIREBASE_API_KEY=…\nVITE_FIREBASE_AUTH_DOMAIN=…\nVITE_FIREBASE_PROJECT_ID=…\nVITE_FIREBASE_STORAGE_BUCKET=…\nVITE_FIREBASE_MESSAGING_SENDER_ID=…\nVITE_FIREBASE_APP_ID=…'}
              </pre>
            </li>
            <li>
              <span className="font-semibold">3.</span> Restart the dev server — Vite reads
              env files only at startup:
              <pre className="mt-1 overflow-x-auto rounded-md bg-slate-900 px-3 py-2 font-mono text-xs text-slate-100">
                yarn dev
              </pre>
            </li>
          </ol>
        </div>

        <div className="card mt-4 p-5">
          <h2 className="card-title">Nothing is wrong with the curriculum data</h2>
          <p className="mt-2 text-sm text-slate-700">
            Grades, subjects, indicators and schedules are committed as static JSON in{' '}
            <code className="font-mono text-xs">public/curriculum/</code> (44 files, 11 grades,
            4,040 indicators). They need no build step to be served — the Python scripts only
            regenerate them from the NaCCA sources when the data itself changes.
          </p>
        </div>

        <p className="card-meta mt-6">
          See <code className="font-mono">docs/build-deploy.md</code> for the full setup, and{' '}
          <code className="font-mono">docs/gotchas.md</code> for this failure mode.
        </p>
      </div>
    </div>
  )
}
