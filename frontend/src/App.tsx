import BackendStatus from './components/BackendStatus'
import { Navigate, NavLink, Route, Routes } from 'react-router'

const pages = [
  { path: '/dashboard', title: 'Dashboard' },
  { path: '/assets', title: 'Assets' },
  { path: '/vulnerabilities', title: 'Vulnerabilities' },
  { path: '/users', title: 'Users' },
  { path: '/audit-logs', title: 'Audit Logs' },
  { path: '/login', title: 'Login' },
  { path: '/register', title: 'Register' },
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


function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h2>VulnFlow</h2>
        <nav aria-label="Main navigation">
          {pages.map((page) => (
            <NavLink
              key={page.path}
              to={page.path}
              className={({ isActive }) =>
                isActive ? 'nav-link active' : 'nav-link'
              }
            >
              {page.title}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="app-main">
        <Routes>
          <Route
            path="/"
            element={<Navigate to="/dashboard" replace />}
          />

          {pages.map((page) => (
            <Route
              key={page.path}
              path={page.path}
              element={<PlaceholderPage title={page.title} />}
            />
          ))}

          <Route
            path="*"
            element={<Navigate to="/dashboard" replace />}
          />
        </Routes>
      </main>
    </div>
  )
}

export default App
