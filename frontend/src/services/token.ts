
export function getTokenExpiration(accessToken: string): number | null {
  const parts = accessToken.split('.')

  if (parts.length !== 3) {
    return null
  }

  try {
    const payload = parts[1]
      .replace(/-/g, '+')
      .replace(/_/g, '/')

    const paddedPayload = payload.padEnd(
      Math.ceil(payload.length / 4) * 4,
      '=',
    )

    const decoded: unknown = JSON.parse(atob(paddedPayload))

    if (
      typeof decoded !== 'object' ||
      decoded === null ||
      !('exp' in decoded) ||
      typeof decoded.exp !== 'number' ||
      !Number.isFinite(decoded.exp)
    ) {
      return null
    }

    return decoded.exp * 1000
  } catch {
    return null
  }
}
