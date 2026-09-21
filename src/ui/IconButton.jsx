import { cn } from './cn'

const VARIANTS = {
  ghost: 'text-muted hover:bg-surface-2 hover:text-heading',
  outline: 'border border-line-2 bg-surface text-muted hover:bg-surface-2 hover:text-heading',
  danger: 'text-danger-600 hover:bg-danger-50 dark:text-danger-500 dark:hover:bg-danger-500/15',
}

const SIZES = {
  sm: 'h-8 w-8',
  md: 'h-10 w-10',
}

/**
 * Icon-only button. `aria-label` is required — an icon button with no accessible
 * name is the exact problem this primitive exists to remove.
 */
export default function IconButton({
  label,
  variant = 'ghost',
  size = 'md',
  className,
  children,
  ...rest
}) {
  return (
    <button
      type={rest.type ?? 'button'}
      aria-label={label}
      title={label}
      className={cn(
        'inline-grid place-items-center rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-50',
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...rest}
    >
      {children}
    </button>
  )
}
