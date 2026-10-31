import { useMemo, useState, type ReactNode } from 'react'

import { AuthContext, type AuthContextValue } from './AuthContext'
import type { AuthSession } from '../services/auth'

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [session, setSession] = useState<AuthSession | null>(null)

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      login: (newSession) => setSession(newSession),
      logout: () => setSession(null),
    }),
    [session],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}
