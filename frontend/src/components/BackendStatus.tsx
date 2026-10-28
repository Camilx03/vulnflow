import { useEffect, useState } from 'react'
import { getHealth } from '../services/api'

type ConnectionStatus = 'checking' | 'online' | 'offline'

export default function BackendStatus() {
  const [connection, setConnection] =
    useState<ConnectionStatus>('checking')

  useEffect(() => {
    const controller = new AbortController()

    async function checkConnection() {
      try {
        const health = await getHealth(controller.signal)

        if (!controller.signal.aborted) {
          setConnection(
            health.status === 'ok' ? 'online' : 'offline',
          )
        }
      } catch {
        if (!controller.signal.aborted) {
          setConnection('offline')
        }
      }
    }

    void checkConnection()

    return () => controller.abort()
  }, [])

  const labels: Record<ConnectionStatus, string> = {
    checking: 'Checking backend connection...',
    online: 'Backend connected',
    offline: 'Backend unavailable',
  }

  return <p role="status">{labels[connection]}</p>
}
