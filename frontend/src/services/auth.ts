export type UserRole = 'admin' | 'analyst' | 'viewer'

export interface CurrentUser {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

interface TokenResponse {
  access_token: string
  token_type: string
}

export interface AuthSession {
  accessToken: string
  user: CurrentUser
}

async function getApiError(response: Response): Promise<Error> {
  if (response.status === 429) {
    const seconds = response.headers.get('Retry-After')

    return new Error(
      seconds
        ? `Demasiados intentos. Prueba de nuevo en ${seconds} segundos.`
        : 'Demasiados intentos. Prueba de nuevo más tarde.',
    )
  }

  const data: unknown = await response.json().catch(() => null)

  if (
    typeof data === 'object' &&
    data !== null &&
    'detail' in data &&
    typeof data.detail === 'string'
  ) {
    return new Error(data.detail)
  }

  return new Error(`Error HTTP ${response.status}`)
}

export async function loginUser(
  email: string,
  password: string,
): Promise<AuthSession> {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  })

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Correo o contraseña incorrectos.')
    }

    throw await getApiError(response)
  }

  const tokens = (await response.json()) as TokenResponse

  if (!tokens.access_token) {
    throw new Error('El servidor no devolvió un token válido.')
  }

  const userResponse = await fetch('/api/v1/auth/me', {
    headers: {
      Authorization: `Bearer ${tokens.access_token}`,
    },
    cache: 'no-store',
  })

  if (!userResponse.ok) {
    throw await getApiError(userResponse)
  }

  const user = (await userResponse.json()) as CurrentUser

  if (!user.is_active) {
    throw new Error('La cuenta está desactivada.')
  }

  return {
    accessToken: tokens.access_token,
    user,
  }
}
