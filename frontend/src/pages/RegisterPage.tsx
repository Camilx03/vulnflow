import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import { registerUser } from '../services/auth'

export default function RegisterPage() {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (loading) return

    setError(null)

    if (fullName.trim().length < 2) {
      setError('El nombre debe tener al menos 2 caracteres.')
      return
    }

    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden.')
      return
    }

    setLoading(true)

    try {
      await registerUser({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
      })

      setSuccess(true)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'No se pudo completar el registro.',
      )
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <section className="auth-panel">
        <h1>Cuenta creada</h1>
        <p>Tu cuenta se ha registrado correctamente.</p>
        <p>
          Ya puedes <Link to="/login">iniciar sesión</Link>.
        </p>
      </section>
    )
  }

  return (
    <section className="auth-panel">
      <h1>Crear cuenta</h1>
      <p>Regístrate para acceder a VulnFlow.</p>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="full-name">Nombre completo</label>
        <input
          id="full-name"
          type="text"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          autoComplete="name"
          minLength={2}
          maxLength={120}
          required
        />

        <label htmlFor="register-email">Correo electrónico</label>
        <input
          id="register-email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
        />

        <label htmlFor="register-password">Contraseña</label>
        <input
          id="register-password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="new-password"
          minLength={12}
          maxLength={128}
          required
        />

        <label htmlFor="confirm-password">Confirmar contraseña</label>
        <input
          id="confirm-password"
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          autoComplete="new-password"
          required
        />

        {error && (
          <p className="auth-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" disabled={loading}>
          {loading ? 'Creando cuenta...' : 'Registrarse'}
        </button>
      </form>

      <p>
        ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
      </p>
    </section>
  )
}
