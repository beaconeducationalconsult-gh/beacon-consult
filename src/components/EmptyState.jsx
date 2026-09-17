export default function EmptyState({ title, message, action, icon = null }) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-12 text-center">
      {icon && <div className="text-slate-300">{icon}</div>}
      <h3 className="font-semibold text-slate-900">{title}</h3>
      {message && <p className="max-w-md text-sm text-slate-500">{message}</p>}
      {action}
    </div>
  )
}
