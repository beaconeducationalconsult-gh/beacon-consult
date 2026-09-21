import { Link } from 'react-router-dom'
import { cn } from './cn'

/** "← Back" navigation link. Pass `to` for a link, or `onClick` for history back. */
export default function BackLink({ to, onClick, children = 'Back', className }) {
  const classes = cn('inline-flex items-center gap-1 text-sm font-medium text-muted hover:text-heading', className)
  if (to) {
    return (
      <Link to={to} className={classes}>
        <span aria-hidden="true">←</span>
        {children}
      </Link>
    )
  }
  return (
    <button type="button" onClick={onClick} className={classes}>
      <span aria-hidden="true">←</span>
      {children}
    </button>
  )
}
