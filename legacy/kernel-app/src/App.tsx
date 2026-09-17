import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Shell } from './ui/layout/Shell'
import { ProtectedRoute } from './ui/layout/ProtectedRoute'
import { LandingPage } from './ui/pages/LandingPage'
import { LoginPage } from './ui/pages/LoginPage'
import { DashboardPage } from './ui/pages/DashboardPage'
import { GeneratePage } from './ui/pages/GeneratePage'
import { HistoryPage } from './ui/pages/HistoryPage'
import { CurriculumPage } from './ui/pages/CurriculumPage'
import { GradePage } from './ui/pages/GradePage'
import { IndicatorListPage } from './ui/pages/IndicatorListPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route index element={<LandingPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="curriculum" element={<CurriculumPage />} />
          <Route path="curriculum/:grade" element={<GradePage />} />
          <Route path="curriculum/:grade/:subject" element={<IndicatorListPage />} />

          {/* Auth-gated */}
          <Route element={<ProtectedRoute />}>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="generate" element={<GeneratePage />} />
            <Route path="history" element={<HistoryPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
