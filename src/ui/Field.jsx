import { forwardRef, useId } from 'react'
import { cn } from './cn'

const CONTROL =
  'w-full rounded-lg border border-line-2 bg-surface px-3 py-2 text-sm text-heading ' +
  'placeholder:text-subtle focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 ' +
  'disabled:bg-surface-2 disabled:text-muted'

export const Input = forwardRef(function Input({ className, ...rest }, ref) {
  return <input ref={ref} className={cn(CONTROL, className)} {...rest} />
})

export const Textarea = forwardRef(function Textarea({ className, ...rest }, ref) {
  return <textarea ref={ref} className={cn(CONTROL, 'min-h-24 resize-y', className)} {...rest} />
})

export const Select = forwardRef(function Select({ className, children, ...rest }, ref) {
  return (
    <select ref={ref} className={cn(CONTROL, 'appearance-none pr-8', className)} {...rest}>
      {children}
    </select>
  )
})

/**
 * Label + control + hint/error. The label is always rendered (never
 * placeholder-only), and `htmlFor` is wired to the control id automatically
 * when the caller does not pass one.
 */
export default function Field({ label, htmlFor, hint, error, required, className, children }) {
  const generated = useId()
  const id = htmlFor || generated
  const hintId = `${id}-hint`
  const errorId = `${id}-error`
  return (
    <div className={cn('space-y-1.5', className)}>
      {label && (
        <label htmlFor={id} className="block text-xs font-semibold uppercase tracking-wide text-muted">
          {label}
          {required && <span className="ml-1 text-danger-600" aria-hidden="true">*</span>}
        </label>
      )}
      {typeof children === 'function' ? children({ id, describedBy: [hint && hintId, error && errorId].filter(Boolean).join(' ') || undefined }) : children}
      {hint && !error && (
        <p id={hintId} className="text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs text-danger-600 dark:text-danger-500">
          {error}
        </p>
      )}
    </div>
  )
}
