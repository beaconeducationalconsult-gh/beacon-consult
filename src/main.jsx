import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Analytics } from '@vercel/analytics/react'
import './index.css'
import App from './App.jsx'
import SetupNotice from './components/SetupNotice'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import { firebaseConfigured } from './firebase'
import { registerServiceWorker } from './registerSW'

const root = createRoot(document.getElementById('root'))

// Without Firebase config nothing else can run: AuthContext subscribes to
// getAuth() and every data hook talks to Firestore. Rendering the app anyway
// used to throw inside module evaluation and leave a blank page — see
// src/components/SetupNotice.jsx.
if (!firebaseConfigured) {
  root.render(
    <StrictMode>
      <SetupNotice />
    </StrictMode>
  )
} else {
  root.render(
    <StrictMode>
      <AuthProvider>
        <BrowserRouter>
          <ToastProvider>
            <App />
            <Analytics />
          </ToastProvider>
        </BrowserRouter>
      </AuthProvider>
    </StrictMode>
  )
}

registerServiceWorker()
