import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'

import { loginUser, type AuthSession } from '../services/auth'

interface LoginPageProps {
  onLogin: (session: AuthSession) => void
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (loading) return

    setLoading(true)
    setError(null)

    try {
      const session = await loginUser(email.trim(), password)

      onLogin(session)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'No se pudo iniciar sesión.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="auth-panel">
      <h1>Iniciar sesión</h1>
      <p>Accede a tu espacio de gestión de vulnerabilidades.</p>

      <form onSubmit={handleSubmit} className="auth-form">
        <label htmlFor="email">Correo electrónico</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
        />

        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />

        {error && <p className="auth-error" role="alert">{error}</p>}

        <button type="submit" disabled={loading}>
          {loading ? 'Iniciando sesión...' : 'Entrar'}
        </button>
      </form>

      <p>
        ¿No tienes cuenta? <Link to="/register">Regístrate</Link>
      </p>
    </section>
  )
}
