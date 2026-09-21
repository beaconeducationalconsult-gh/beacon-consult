import { Card } from '../ui/Card'

export default function EmptyState({ title, message, action, icon = null }) {
  return (
    <Card className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      {icon && <div className="text-subtle">{icon}</div>}
      <h3 className="font-semibold text-heading">{title}</h3>
      {message && <p className="max-w-md text-sm text-muted">{message}</p>}
      {action}
    </Card>
  )
}
