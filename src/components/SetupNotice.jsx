/**
 * Shown instead of the app when the six VITE_FIREBASE_* values were missing
 * when this build was compiled.
 *
 * Before this screen existed, a missing config threw `auth/invalid-api-key`
 * while the entry module was evaluating, so the page stayed blank and nothing
 * said why. The curriculum data is static JSON in `public/curriculum/` and is
 * already present — it is Firebase, not the data, that is missing here.
 *
 * The instructions depend on where the reader is standing, and the two fixes do
 * not overlap: a dev server needs `.env.local` and a restart, a deploy needs the
 * values in the *build* environment and a rebuild. `src/lib/setupGuidance.js`
 * owns both copies (and is what the tests assert); this component only renders
 * them.
 */
import { setupNoticeCopy, setupNoticeMode } from '../lib/setupGuidance'
import { missingFirebaseEnv } from '../firebase'

export default function SetupNotice() {
  const copy = setupNoticeCopy({
    mode: setupNoticeMode({ prod: import.meta.env.PROD, hostname: window.location.hostname }),
    missing: missingFirebaseEnv,
    origin: window.location.origin,
  })

  return (
    <div className="min-h-screen bg-bg px-4 py-12">
      <div className="mx-auto max-w-2xl">
        <p className="section-heading">Beacon Consult</p>
        <h1 className="page-title mt-2">{copy.title}</h1>
        <p className="page-subtitle mt-2">{copy.lead}</p>

        {copy.mode === 'local' && copy.missing.length > 0 && (
          <p className="card-meta mt-2">Not found in this build: {copy.missing.join(', ')}</p>
        )}

        <div className="card mt-6 p-5">
          <h2 className="card-title">{copy.mode === 'deploy' ? 'Set them on Vercel, then re-deploy' : 'Add the six values'}</h2>
          <ol className="mt-3 space-y-3 text-sm text-text">
            {copy.steps.map((step, index) => (
              <li key={step.title}>
                <span className="font-semibold">{index + 1}.</span> {step.title}
                {step.code ? (
                  // Terminal-style code block: stays dark in both themes on purpose.
                  <pre className="mt-1 overflow-x-auto rounded-md bg-slate-900 px-3 py-2 font-mono text-xs text-slate-100">
                    {step.code}
                  </pre>
                ) : null}
              </li>
            ))}
          </ol>
          {copy.note ? <p className="card-meta mt-4">{copy.note}</p> : null}
        </div>

        <div className="card mt-4 p-5">
          <h2 className="card-title">{copy.curriculum.title}</h2>
          <p className="mt-2 text-sm text-text">{copy.curriculum.body}</p>
        </div>

        <p className="card-meta mt-6">{copy.footnote}</p>
      </div>
    </div>
  )
}
