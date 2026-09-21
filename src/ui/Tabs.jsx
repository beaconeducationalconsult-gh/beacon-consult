import { cn } from './cn'

/**
 * Accessible tab strip (controlled). Roving tabindex + arrow/Home/End keys.
 * Consumers render the matching panel; this is only the tablist, matching the
 * existing NotesTabs contract ({ tabs, active, onChange }).
 */
export default function Tabs({ tabs, active, onChange, className, idPrefix = 'tab' }) {
  const values = tabs.map((t) => t.value)
  const activeIndex = Math.max(0, values.indexOf(active))

  const onKeyDown = (event) => {
    let next = null
    if (event.key === 'ArrowRight') next = (activeIndex + 1) % values.length
    else if (event.key === 'ArrowLeft') next = (activeIndex - 1 + values.length) % values.length
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = values.length - 1
    if (next == null) return
    event.preventDefault()
    const tab = tabs[next]
    onChange(tab.value)
    document.getElementById(`${idPrefix}-${tab.value}`)?.focus()
  }

  return (
    <div role="tablist" onKeyDown={onKeyDown} className={cn('flex gap-1 overflow-x-auto border-b border-line', className)}>
      {tabs.map((tab) => {
        const isActive = tab.value === active
        return (
          <button
            key={tab.value}
            id={`${idPrefix}-${tab.value}`}
            role="tab"
            type="button"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(tab.value)}
            className={cn(
              '-mb-px whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-semibold transition-colors',
              isActive
                ? 'border-primary text-primary'
                : 'border-transparent text-muted hover:border-line-2 hover:text-heading'
            )}
          >
            {tab.label}
            {tab.count != null && <span className="ml-2 text-xs text-subtle">{tab.count}</span>}
          </button>
        )
      })}
    </div>
  )
}
