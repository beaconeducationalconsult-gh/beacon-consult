import { subjectTheme } from '../lib/subjectThemes'

/**
 * Per-subject icon: a tinted monogram. Keeps the app free of an icon
 * dependency while still giving each subject a recognisable mark.
 */
export default function SubjectIcon({ subjectId, name, size = 'md' }) {
  const theme = subjectTheme(subjectId)
  const initials = String(name || subjectId || '?')
    .split(/\s+/)
    .filter((w) => /[a-z]/i.test(w))
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('')

  const dims = size === 'sm' ? 'h-8 w-8 text-xs' : size === 'lg' ? 'h-14 w-14 text-lg' : 'h-10 w-10 text-sm'

  return (
    <span
      aria-hidden="true"
      className={`grid shrink-0 place-items-center rounded-xl border font-bold ${theme.bg} ${theme.text} ${theme.border} ${dims}`}
    >
      {initials || '•'}
    </span>
  )
}
