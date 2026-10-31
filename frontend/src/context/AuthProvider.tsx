
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { AuthContext, type AuthContextValue } from './AuthContext'
import type { AuthSession } from '../services/auth'
import { getTokenExpiration } from '../services/token'

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [session, setSession] = useState<AuthSession | null>(null)

  const logout = useCallback(() => {
    setSession(null)
  }, [])

  const login = useCallback((newSession: AuthSession) => {
    const expiresAt = getTokenExpiration(newSession.accessToken)

    if (expiresAt === null || expiresAt <= Date.now()) {
      throw new Error('El token de sesión no es válido o ha caducado.')
    }

    setSession(newSession)
  }, [])

  const authFetch = useCallback(
    async (path: string, options?: RequestInit): Promise<Response> => {
      if (!path.startsWith('/api/v1/')) {
        throw new Error('La ruta de la API no es válida.')
      }

      if (!session) {
        throw new Error('No hay una sesión activa.')
      }

      const accessToken = session.accessToken
      const headers = new Headers(options?.headers)

      headers.set('Authorization', `Bearer ${accessToken}`)

      const response = await fetch(path, {
        ...options,
        headers,
        cache: 'no-store',
      })

      if (response.status === 401 && !options?.signal?.aborted) {
        setSession((currentSession) =>
          currentSession?.accessToken === accessToken
            ? null
            : currentSession,
        )
      }

      return response
    },
    [session],
  )

  useEffect(() => {
    if (!session) {
      return
    }

    const accessToken = session.accessToken
    const expiresAt = getTokenExpiration(accessToken)

    const remainingMs =
      expiresAt === null
        ? 0
        : Math.max(0, expiresAt - Date.now())

    const timeoutId = window.setTimeout(logout, remainingMs)
    const controller = new AbortController()

    let checkingSession = false

    async function verifySession() {
      if (expiresAt === null || Date.now() >= expiresAt) {
        logout()
        return
      }

      if (checkingSession) {
        return
      }

      checkingSession = true

      try {
        const response = await authFetch('/api/v1/auth/me', {
          signal: controller.signal,
        })

        if (
          response.status === 403 &&
          !controller.signal.aborted
        ) {
          setSession((currentSession) =>
            currentSession?.accessToken === accessToken
              ? null
              : currentSession,
          )
        }
      } catch {
        return
      } finally {
        checkingSession = false
      }
    }

    function handleFocus() {
      void verifySession()
    }

    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') {
        void verifySession()
      }
    }

    window.addEventListener('focus', handleFocus)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      controller.abort()
      window.clearTimeout(timeoutId)
      window.removeEventListener('focus', handleFocus)
      document.removeEventListener(
        'visibilitychange',
        handleVisibilityChange,
      )
    }
  }, [session, logout, authFetch])

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      login,
      logout,
      authFetch,
    }),
    [session, login, logout, authFetch],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}
