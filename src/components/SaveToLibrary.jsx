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
  const { save, saving, available } = useLibrarySave()
  if (!available) return null

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
