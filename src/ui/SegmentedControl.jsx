import { cn } from './cn'

/**
 * Segmented control / pill toggle (controlled). Radiogroup semantics with
 * roving tabindex and arrow-key movement. Replaces the hand-rolled
 * `rounded-full` active/inactive pills duplicated across SignUp, Profile,
 * QuestionForm and Wisdom.
 */
export default function SegmentedControl({ options, value, onChange, label, className, size = 'md' }) {
  const values = options.map((o) => o.value)
  const activeIndex = Math.max(0, values.indexOf(value))

  const move = (delta) => {
    const next = (activeIndex + delta + values.length) % values.length
    onChange(values[next])
  }

  const onKeyDown = (event) => {
    if (event.key === 'ArrowRight') {
      event.preventDefault()
      move(1)
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      move(-1)
    }
  }

  const pad = size === 'sm' ? 'px-3 py-1 text-xs' : 'px-4 py-1.5 text-sm'

  return (
    <div
      role="radiogroup"
      aria-label={label}
      onKeyDown={onKeyDown}
      className={cn('inline-flex flex-wrap gap-1 rounded-full bg-surface-2 p-1', className)}
    >
      {options.map((option) => {
        const isActive = option.value === value
        return (
          <button
            key={option.value}
            role="radio"
            type="button"
            aria-checked={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(option.value)}
            className={cn(
              'rounded-full font-medium transition-colors',
              pad,
              isActive
                ? 'bg-surface text-heading shadow-card'
                : 'text-muted hover:text-heading'
            )}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
