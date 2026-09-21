import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'
import Footer from './Footer'

/**
 * Shared chrome for the public marketing/auth pages: one Navbar and one Footer
 * around every public route, so pages no longer render their own Navbar and
 * only-Landing-had-a-footer inconsistency goes away.
 */
export default function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <Navbar />
      {/* Plain wrapper, not <main>: several public pages render their own
          <main> landmark and nesting two would break the document outline. */}
      <div className="flex-1">
        <Outlet />
      </div>
      <Footer />
    </div>
  )
}
