import {
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
} from 'react-router'

import BackendStatus from './components/BackendStatus'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import type { UserRole } from './services/auth'
import { useAuth } from './context/AuthContext'

interface Page {
  path: string
  title: string
  roles: UserRole[]
}

const pages: Page[] = [
  {
    path: '/dashboard',
    title: 'Dashboard',
    roles: ['admin', 'analyst', 'viewer'],
  },
  {
    path: '/assets',
    title: 'Assets',
    roles: ['admin', 'analyst', 'viewer'],
  },
  {
    path: '/vulnerabilities',
    title: 'Vulnerabilities',
    roles: ['admin', 'analyst', 'viewer'],
  },
  {
    path: '/users',
    title: 'Users',
    roles: ['admin', 'analyst'],
  },
  {
    path: '/audit-logs',
    title: 'Audit Logs',
    roles: ['admin'],
  },
]

function PlaceholderPage({ title }: { title: string }) {
  return (
    <section>
      <h1>{title}</h1>
      <p>This section is under development.</p>
      {title === 'Dashboard' && <BackendStatus />}
    </section>
  )
}

function ProtectedArea() {
  const { session } = useAuth()

  if (!session) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

function App() {
  const { session, logout } = useAuth()

  const visiblePages = session
    ? pages.filter((page) =>
      page.roles.includes(session.user.role),
    )
    : []


  return (
    <div className="app">
      <header className="app-header">
        <h2>VulnFlow</h2>

        <nav aria-label="Main navigation">
          {session ? (
            visiblePages.map((page) => (
              <NavLink
                key={page.path}
                to={page.path}
                className={({ isActive }) =>
                  isActive ? 'nav-link active' : 'nav-link'
                }
              >
                {page.title}
              </NavLink>
            ))
          ) : (
            <>
              <NavLink to="/login" className="nav-link">
                Login
              </NavLink>
              <NavLink to="/register" className="nav-link">
                Register
              </NavLink>
            </>
          )}
        </nav>

        {session && (
          <div className="session-info">
            <span>
              {session.user.full_name} ({session.user.role})
            </span>
            <button type="button" onClick={logout}>
              Cerrar sesión
            </button>
          </div>
        )}
      </header>

      <main className="app-main">
        <Routes>
          <Route
            path="/"
            element={
              <Navigate
                to={session ? '/dashboard' : '/login'}
                replace
              />
            }
          />

          <Route
            path="/login"
            element={
              session ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <LoginPage />
              )
            }
          />

          <Route
            path="/register"
            element={
              session ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <RegisterPage />
              )
            }
          />

          <Route element={<ProtectedArea />}>
            {pages.map((page) => (
              <Route
                key={page.path}
                path={page.path}
                element={
                  session &&
                    page.roles.includes(session.user.role) ? (
                    <PlaceholderPage title={page.title} />
                  ) : (
                    <Navigate to="/dashboard" replace />
                  )
                }
              />
            ))}
          </Route>

          <Route
            path="*"
            element={
              <Navigate
                to={session ? '/dashboard' : '/login'}
                replace
              />
            }
          />
        </Routes>
      </main>
    </div>
  )
}

export default App
