import { cn } from './cn'

const VARIANTS = {
  primary: 'bg-primary text-on-primary hover:bg-primary-hover',
  secondary: 'border border-line-2 bg-surface text-text hover:bg-surface-2',
  accent: 'bg-accent-500 text-ink hover:bg-accent-400',
  danger: 'bg-danger-600 text-white hover:bg-danger-700',
  ghost: 'text-muted hover:bg-surface-2 hover:text-heading',
}

const SIZES = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
}

const BASE =
  'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors ' +
  'disabled:cursor-not-allowed disabled:opacity-50'

function Spinner() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 animate-spin" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

/**
 * The one button. Variant sets colour, size sets box — they never touch the same
 * CSS property, so no class-merge step is needed.
 */
export default function Button({
  as: Component = 'button',
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  className,
  children,
  ...rest
}) {
  const isButton = Component === 'button'
  return (
    <Component
      className={cn(BASE, VARIANTS[variant], SIZES[size], className)}
      disabled={isButton ? disabled || loading : undefined}
      aria-busy={loading || undefined}
      {...(isButton && rest.type == null ? { type: 'button' } : {})}
      {...rest}
    >
      {loading && <Spinner />}
      {children}
    </Component>
  )
}
