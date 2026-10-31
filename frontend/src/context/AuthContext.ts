import { createContext, useContext } from 'react'

import type { AuthSession } from '../services/auth'

export interface AuthContextValue {
  session: AuthSession | null
  login: (session: AuthSession) => void
  logout: () => void
  authFetch: (path: string, options?: RequestInit) => Promise<Response>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)

  if (context === null) {
    throw new Error('useAuth must be used within AuthProvider')
  }

  return context
}
