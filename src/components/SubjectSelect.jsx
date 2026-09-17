import { gradeLabel } from '../lib/grades'

/**
 * Subject dropdown for one grade, backed by
 * `public/curriculum/<grade>_subjects.json`.
 *
 * A drop-in replacement for the hand-rolled `<select>` it replaces: pass the
 * `subjects` / `loading` / `error` values from `useCurriculum` plus the usual
 * select props (`id`, `value`, `onChange`, `disabled`).
 *
 * The curriculum is static JSON committed to the repo, so an empty list always
 * means the fetch failed — offline, a stale service worker, or a 404 because
 * the app is not served from the domain root. That used to be invisible: the
 * select rendered just "Choose…", which looks identical to "this grade has no
 * subjects". Say it out loud instead of failing silently.
 */
export default function SubjectSelect({
  subjects = [],
  loading = false,
  error = null,
  grade,
  ...selectProps
}) {
  const failed = Boolean(error) && subjects.length === 0
  const empty = !loading && !failed && subjects.length === 0
  const label = gradeLabel(grade)

  return (
    <>
      <select {...selectProps}>
        <option value="">{loading ? 'Loading subjects…' : 'Choose…'}</option>
        {subjects.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>

      {failed && (
        <p role="alert" className="mt-1 text-xs text-amber-700">
          Could not load the {label ? `${label} ` : ''}subject list. Check your connection,
          then reload.
        </p>
      )}

      {empty && (
        <p className="mt-1 text-xs text-slate-500">No subjects are listed for this grade.</p>
      )}
    </>
  )
}
