
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthContext, type AuthContextValue } from '../context/AuthContext'
import DashboardPage from './DashboardPage'

const dashboardStats = {
  total_assets: 5,
  total_vulnerabilities: 4,
  affected_assets: 2,
  unassigned_vulnerabilities: 1,
  active_vulnerabilities: 3,
  by_severity: {
    critical: 0,
    high: 2,
    medium: 1,
    low: 0,
    info: 1,
  },
  by_status: {
    open: 2,
    in_progress: 1,
    resolved: 1,
    accepted_risk: 0,
    false_positive: 0,
  },
}

function mockApi(status: number, data: unknown = {}) {
  const authFetch = vi.fn<AuthContextValue['authFetch']>()

  authFetch.mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  } as Response)

  return authFetch
}

function renderDashboard(authFetch: AuthContextValue['authFetch']) {
  return render(
    <AuthContext.Provider
      value={{
        session: null,
        login: vi.fn(),
        logout: vi.fn(),
        authFetch,
      }}
    >
      <DashboardPage />
    </AuthContext.Provider>,
  )
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('DashboardPage', () => {
  it('muestra los indicadores reales recibidos de la API', async () => {
    const authFetch = mockApi(200, dashboardStats)

    renderDashboard(authFetch)

    await screen.findByText('Activos totales')

    expect(
      screen.getByText('Activos totales').parentElement,
    ).toHaveTextContent('5')

    expect(
      screen.getByText('Vulnerabilidades').parentElement,
    ).toHaveTextContent('4')

    expect(
      screen.getByText('Vulnerabilidades activas').parentElement,
    ).toHaveTextContent('3')

    expect(
      screen.getByText('Activos afectados').parentElement,
    ).toHaveTextContent('2')

    expect(
      screen.getByText('Sin asignar').parentElement,
    ).toHaveTextContent('1')

    expect(
      screen.getByRole('progressbar', { name: /Alta: 2/ }),
    ).toBeInTheDocument()

    expect(
      screen.getByRole('progressbar', { name: /Abierta: 2/ }),
    ).toBeInTheDocument()

    expect(authFetch).toHaveBeenCalledWith(
      '/api/v1/dashboard/stats',
      { signal: expect.any(AbortSignal) },
    )
  })

  it('muestra un indicador mientras se cargan los datos', () => {
    const authFetch = vi.fn<AuthContextValue['authFetch']>()

    authFetch.mockImplementation(
      () => new Promise<Response>(() => {}),
    )

    renderDashboard(authFetch)

    expect(screen.getByRole('status')).toHaveTextContent(
      'Cargando indicadores...',
    )
  })

  it('muestra un mensaje cuando no hay vulnerabilidades', async () => {
    const emptyStats = {
      total_assets: 0,
      total_vulnerabilities: 0,
      affected_assets: 0,
      unassigned_vulnerabilities: 0,
      active_vulnerabilities: 0,
      by_severity: {},
      by_status: {},
    }

    renderDashboard(mockApi(200, emptyStats))

    expect(
      await screen.findByText(
        'Todavía no hay vulnerabilidades registradas.',
      ),
    ).toBeInTheDocument()
  })

  it('muestra un error si el servidor responde HTTP 500', async () => {
    renderDashboard(mockApi(500))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudieron cargar los indicadores del dashboard.',
    )
  })

  it('muestra un error si falla la conexión', async () => {
    const authFetch = vi.fn<AuthContextValue['authFetch']>()

    authFetch.mockRejectedValue(
      new Error('Connection refused'),
    )

    renderDashboard(authFetch)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudieron cargar los indicadores del dashboard.',
    )
  })
})
