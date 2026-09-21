import { cn } from './cn'

const SIZES = {
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-16 w-16 text-xl',
}

/** Initial-circle avatar. Falls back to the first letter of `name`. */
export default function Avatar({ name = '', src, alt = '', size = 'md', className }) {
  const initial = (name.trim()[0] || '?').toUpperCase()
  if (src) {
    return (
      <img
        src={src}
        alt={alt || name}
        className={cn('rounded-full object-cover', SIZES[size], className)}
      />
    )
  }
  return (
    <span
      role="img"
      aria-label={alt || name}
      className={cn('grid place-items-center rounded-full bg-brand-600 font-bold text-white', SIZES[size], className)}
    >
      {initial}
    </span>
  )
}
