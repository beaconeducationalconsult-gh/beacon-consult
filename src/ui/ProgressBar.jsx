import { cn } from './cn'

/**
 * Determinate progress bar. `value` is 0–100 (clamped). Decorative by default;
 * pass `label` to expose it to assistive tech.
 */
export default function ProgressBar({ value = 0, label, tone = 'primary', className, barClassName }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)))
  const fill = tone === 'accent' ? 'bg-accent-500' : tone === 'success' ? 'bg-success-500' : 'bg-primary'
  return (
    <div
      role={label ? 'progressbar' : undefined}
      aria-label={label}
      aria-valuenow={label ? pct : undefined}
      aria-valuemin={label ? 0 : undefined}
      aria-valuemax={label ? 100 : undefined}
      className={cn('h-2 w-full overflow-hidden rounded-full bg-surface-2', className)}
    >
      <div className={cn('h-full rounded-full transition-[width] duration-300', fill, barClassName)} style={{ width: `${pct}%` }} />
    </div>
  )
}
