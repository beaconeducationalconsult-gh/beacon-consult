import { cn } from './cn'

export function Card({ hover = false, className, children, ...rest }) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-line-2 bg-surface shadow-card',
        hover && 'transition-shadow hover:shadow-pop',
        className
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

export function CardHeader({ className, children, ...rest }) {
  return (
    <div className={cn('flex items-start justify-between gap-3 border-b border-line-2 px-5 py-4', className)} {...rest}>
      {children}
    </div>
  )
}

export function CardBody({ className, children, ...rest }) {
  return (
    <div className={cn('px-5 py-4', className)} {...rest}>
      {children}
    </div>
  )
}

export function CardFooter({ className, children, ...rest }) {
  return (
    <div className={cn('flex items-center justify-end gap-2 border-t border-line-2 px-5 py-4', className)} {...rest}>
      {children}
    </div>
  )
}
