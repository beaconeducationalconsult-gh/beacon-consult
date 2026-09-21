import { cn } from './cn'

const TONES = {
  neutral: 'bg-surface-2 text-muted',
  brand: 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300',
  success: 'bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-500',
  warning: 'bg-warning-50 text-warning-700 dark:bg-warning-500/15 dark:text-warning-500',
  danger: 'bg-danger-50 text-danger-700 dark:bg-danger-500/15 dark:text-danger-500',
  info: 'bg-info-50 text-info-700 dark:bg-info-500/15 dark:text-info-500',
}

export default function Badge({ tone = 'neutral', className, children, ...rest }) {
  return (
    <span
      className={cn('inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium', TONES[tone], className)}
      {...rest}
    >
      {children}
    </span>
  )
}
