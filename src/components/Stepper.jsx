export default function Stepper({ steps, current = 0, onStep }) {
  return (
    <ol className="mb-6 flex flex-wrap items-center gap-x-2 gap-y-2">
      {steps.map((step, index) => {
        const state = index === current ? 'current' : index < current ? 'done' : 'todo'
        return (
          <li key={step} className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onStep?.(index)}
              aria-current={state === 'current' ? 'step' : undefined}
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                state === 'current'
                  ? 'bg-brand-600 text-white'
                  : state === 'done'
                    ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300'
                    : 'bg-surface-2 text-muted'
              }`}
            >
              <span
                className={`grid h-5 w-5 place-items-center rounded-full text-[10px] ${
                  state === 'current' ? 'bg-white/20' : 'bg-surface'
                }`}
              >
                {state === 'done' ? '✓' : index + 1}
              </span>
              {step}
            </button>
            {index < steps.length - 1 && <span className="text-subtle">→</span>}
          </li>
        )
      })}
    </ol>
  )
}
