import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../services/AuthContext'

export function ProtectedRoute() {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-8 text-center">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}
