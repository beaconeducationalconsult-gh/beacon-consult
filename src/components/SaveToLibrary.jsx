import { useLibrarySave } from '../hooks/useLibrarySave'

/**
 * The button that stores a generated document in the member's library (P3-3).
 *
 * One line per page: `<SaveToLibrary kind="lesson_plan" meta={{…}}
 * filename="…" build={() => downloadLessonPlanDocx(plan, meta)} />`. The build
 * function runs only when the button is pressed, and only when the member could
 * actually store the result.
 */
export default function SaveToLibrary({ kind, filename, meta, build, label = 'Save to library' }) {
  const { save, saving, available, missing } = useLibrarySave()
  if (!available) {
    // A project with no Storage bucket (Cloud Storage needs the Blaze plan) is
    // not an error state — the export still works. Say so once, quietly, rather
    // than leaving a button that can only fail.
    return missing
      ? (
        <p className="card-meta" data-testid="library-unavailable">
          Keeping documents in the portal needs Firebase Storage, which this project does not have
          enabled. The download above is yours to keep.
        </p>
      )
      : null
  }

  return (
    <button
      type="button"
      className="btn-secondary"
      disabled={saving}
      onClick={() => save(build, { kind, filename, meta })}
    >
      {saving ? 'Saving…' : label}
    </button>
  )
}
