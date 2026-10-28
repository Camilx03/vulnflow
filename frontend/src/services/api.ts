export interface HealthResponse {
  status: string
  service: string
}

export async function getHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  const response = await fetch('/api/v1/health', {
    signal,
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return (await response.json()) as HealthResponse
}
