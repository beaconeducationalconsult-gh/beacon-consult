import { Link } from 'react-router-dom'
import { useAuth } from '../../services/AuthContext'
import { signOutUser } from '../../services/auth'

export function Navbar() {
  const { user } = useAuth()

  return (
    <nav className="bg-[#1B4332] text-[#F1E9D8] px-4 py-3 flex items-center justify-between">
      <Link to="/" className="font-display font-bold text-lg">
        NCOS
      </Link>
      <div className="flex items-center gap-4">
        <Link to="/curriculum" className="text-sm hover:text-[#C89B3C]">Curriculum</Link>
        {user ? (
          <>
            <Link to="/dashboard" className="text-sm hover:text-[#C89B3C]">Dashboard</Link>
            <Link to="/generate" className="text-sm hover:text-[#C89B3C]">Generate</Link>
            <button
              onClick={() => signOutUser()}
              className="text-sm bg-[#16201A] px-3 py-1 rounded hover:bg-black transition-colors"
            >
              Sign Out
            </button>
          </>
        ) : (
          <Link to="/login" className="text-sm bg-[#C89B3C] text-[#16201A] px-3 py-1 rounded font-medium hover:bg-[#d4a546] transition-colors">
            Sign In
          </Link>
        )}
      </div>
    </nav>
  )
}
