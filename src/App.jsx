import { Suspense, lazy } from 'react'
import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Sidebar from './components/Sidebar'
import PendingApproval from './components/PendingApproval'
import OfflineIndicator from './components/OfflineIndicator'
import { SkeletonList } from './components/Skeleton'

// Public pages — eager (they're the first thing a visitor sees).
import Landing from './pages/Landing'
import Login from './pages/Login'
import SignUp from './pages/SignUp'
import PublicVacancies from './pages/PublicVacancies'
import PublicQuotes from './pages/PublicQuotes'
import PublicCalendar from './pages/PublicCalendar'
import PublicArticles from './pages/PublicArticles'
import PublicArticleView from './pages/PublicArticleView'

// Portal pages — lazy so the public landing stays small.
const Workspace = lazy(() => import('./pages/Workspace'))
const Curriculum = lazy(() => import('./pages/Curriculum'))
const GradeSubjects = lazy(() => import('./pages/GradeSubjects'))
const SubjectBrowser = lazy(() => import('./pages/SubjectBrowser'))
const Wisdom = lazy(() => import('./pages/Wisdom'))
const Articles = lazy(() => import('./pages/Articles'))
const ArticleForm = lazy(() => import('./pages/ArticleForm'))
const ArticleView = lazy(() => import('./pages/ArticleView'))
const Forecasts = lazy(() => import('./pages/Forecasts'))
const ForecastForm = lazy(() => import('./pages/ForecastForm'))
const ForecastView = lazy(() => import('./pages/ForecastView'))
const LessonPlans = lazy(() => import('./pages/LessonPlans'))
const LessonPlanForm = lazy(() => import('./pages/LessonPlanForm'))
const LessonPlanView = lazy(() => import('./pages/LessonPlanView'))
const QuestionBank = lazy(() => import('./pages/QuestionBank'))
const QuestionForm = lazy(() => import('./pages/QuestionForm'))
const QuestionGenerator = lazy(() => import('./pages/QuestionGenerator'))
const QuizMaker = lazy(() => import('./pages/QuizMaker'))
const Notes = lazy(() => import('./pages/Notes'))
const NoteForm = lazy(() => import('./pages/NoteForm'))
const NoteView = lazy(() => import('./pages/NoteView'))
const AuthorPage = lazy(() => import('./pages/AuthorPage'))
const Vacancies = lazy(() => import('./pages/Vacancies'))
const VacancyForm = lazy(() => import('./pages/VacancyForm'))
const SlideLessons = lazy(() => import('./pages/SlideLessons'))
const Search = lazy(() => import('./pages/Search'))
const Progress = lazy(() => import('./pages/Progress'))
const Profile = lazy(() => import('./pages/Profile'))
const Members = lazy(() => import('./pages/Members'))

/**
 * The portal gate.
 *
 * This is UX only — the real enforcement is `firestore.rules`, which rejects
 * unapproved reads/writes at the data layer regardless of what renders here.
 * See docs/security.md.
 */
function ProtectedLayout() {
  const { user, profile, loading, canUsePortal } = useAuth()

  if (loading || (user && profile === undefined)) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16">
        <SkeletonList rows={4} />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  if (!canUsePortal) return <PendingApproval suspended={profile?.status === 'suspended'} />

  return (
    <div className="min-h-screen bg-cream lg:ml-56">
      <Sidebar />
      <main className="mx-auto max-w-5xl px-4 pb-24 pt-6 lg:pt-10">
        <Suspense
          fallback={
            <div className="py-8">
              <SkeletonList rows={3} />
            </div>
          }
        >
          <Outlet />
        </Suspense>
      </main>
      <OfflineIndicator />
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      {/* ── Public ─────────────────────────────────────────────────────── */}
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<SignUp />} />
      <Route path="/vacancies" element={<PublicVacancies />} />
      <Route path="/quotes" element={<PublicQuotes />} />
      <Route path="/calendar" element={<PublicCalendar />} />
      <Route path="/articles" element={<PublicArticles />} />
      <Route path="/articles/:articleId" element={<PublicArticleView />} />

      {/* ── Portal (approved members only) ─────────────────────────────── */}
      <Route path="/portal" element={<ProtectedLayout />}>
        <Route index element={<Workspace />} />
        <Route path="curriculum" element={<Curriculum />} />
        <Route path="curriculum/:gradeId" element={<GradeSubjects />} />
        <Route path="curriculum/:gradeId/:subjectId" element={<SubjectBrowser />} />
        <Route path="wisdom" element={<Wisdom />} />

        <Route path="articles" element={<Articles />} />
        <Route path="articles/new" element={<ArticleForm />} />
        <Route path="articles/:articleId" element={<ArticleView />} />
        <Route path="articles/:articleId/edit" element={<ArticleForm />} />

        <Route path="forecasts" element={<Forecasts />} />
        <Route path="forecasts/new" element={<ForecastForm />} />
        <Route path="forecasts/:forecastId" element={<ForecastView />} />
        <Route path="forecasts/:forecastId/edit" element={<ForecastForm />} />

        <Route path="plans" element={<LessonPlans />} />
        <Route path="plans/new" element={<LessonPlanForm />} />
        <Route path="plans/:planId" element={<LessonPlanView />} />
        <Route path="plans/:planId/edit" element={<LessonPlanForm />} />

        <Route path="questions" element={<QuestionBank />} />
        <Route path="questions/new" element={<QuestionForm />} />
        <Route path="questions/generate" element={<QuestionGenerator />} />
        <Route path="questions/quiz" element={<QuizMaker />} />
        <Route path="questions/:questionId/edit" element={<QuestionForm />} />

        <Route path="notes" element={<Notes />} />
        <Route path="notes/new" element={<NoteForm />} />
        <Route path="notes/:noteId" element={<NoteView />} />
        <Route path="notes/:noteId/edit" element={<NoteForm />} />

        <Route path="vacancies" element={<Vacancies />} />
        <Route path="vacancies/new" element={<VacancyForm />} />
        <Route path="vacancies/:vacancyId/edit" element={<VacancyForm />} />

        <Route path="slides" element={<SlideLessons />} />

        {/* Folded into the workspace: /portal and /portal/wall are one page now. */}
        <Route path="wall" element={<Navigate to="/portal" replace />} />
        <Route path="authors/:authorId" element={<AuthorPage />} />
        <Route path="search" element={<Search />} />
        <Route path="progress" element={<Progress />} />
        <Route path="calendar" element={<Navigate to="/portal" replace />} />
        <Route path="profile" element={<Profile />} />
        <Route path="members" element={<Members />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
