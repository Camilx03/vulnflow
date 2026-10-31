
import {
    cleanup,
    fireEvent,
    render,
    screen,
    within,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
    AuthContext,
    type AuthContextValue,
} from '../context/AuthContext'
import AssetsPage from './AssetsPage'

const assets = [
    {
        id: 'asset-development',
        hostname: 'srv-development-01',
        ip_address: '10.0.0.30',
        operating_system: 'Ubuntu 24.04',
        environment: 'development',
        description: 'Development application server',
        created_at: '2026-09-10T18:53:33Z',
        updated_at: '2026-09-10T18:53:33Z',
    },
    {
        id: 'asset-production',
        hostname: 'srv-production-01',
        ip_address: '10.0.0.15',
        operating_system: 'Ubuntu 24.04',
        environment: 'production',
        description: 'Production application server',
        created_at: '2026-09-10T18:53:33Z',
        updated_at: '2026-09-10T18:53:33Z',
    },
]

function renderAssets(status = 200) {
    const authFetch = vi.fn<AuthContextValue['authFetch']>()

    authFetch.mockResolvedValue({
        ok: status >= 200 && status < 300,
        status,
        json: async () => assets,
    } as Response)

    render(
        <AuthContext.Provider
            value={{
                session: null,
                login: vi.fn(),
                logout: vi.fn(),
                authFetch,
            }}
        >
            <AssetsPage />
        </AuthContext.Provider>,
    )

    return authFetch
}

afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
})

describe('AssetsPage', () => {
    it('carga los activos desde FastAPI', async () => {
        const authFetch = renderAssets()

        expect(
            await screen.findByText('srv-development-01'),
        ).toBeInTheDocument()

        expect(
            screen.getByText('srv-production-01'),
        ).toBeInTheDocument()

        expect(
            screen.getByText('Mostrando 2 de 2 activos'),
        ).toBeInTheDocument()

        expect(authFetch).toHaveBeenCalledWith(
            '/api/v1/assets',
            { signal: expect.any(AbortSignal) },
        )
    })

    it('filtra los activos por hostname', async () => {
        renderAssets()

        await screen.findByText('srv-development-01')

        fireEvent.change(
            screen.getByRole('searchbox', {
                name: 'Buscar activos',
            }),
            {
                target: {
                    value: 'srv-production-01',
                },
            },
        )

        expect(
            screen.getByText('srv-production-01'),
        ).toBeInTheDocument()

        expect(
            screen.queryByText('srv-development-01'),
        ).not.toBeInTheDocument()

        expect(
            screen.getByText('Mostrando 1 de 2 activos'),
        ).toBeInTheDocument()
    })

    it('permite abrir y cerrar los detalles', async () => {
        renderAssets()

        await screen.findByText('srv-development-01')

        fireEvent.click(
            screen.getAllByRole('button', {
                name: 'Ver detalles',
            })[0],
        )

        expect(
            screen.getByRole('heading', {
                name: 'Detalles del activo',
            }),
        ).toBeInTheDocument()

        expect(
            screen.getByText('Development application server'),
        ).toBeInTheDocument()

        fireEvent.click(
            screen.getByRole('button', {
                name: 'Cerrar',
            }),
        )

        expect(
            screen.queryByRole('heading', {
                name: 'Detalles del activo',
            }),
        ).not.toBeInTheDocument()
    })

    it('cierra los detalles anteriores al cambiar la búsqueda', async () => {
        renderAssets()

        await screen.findByText('srv-development-01')

        fireEvent.click(
            screen.getAllByRole('button', {
                name: 'Ver detalles',
            })[0],
        )

        expect(
            screen.getByText('Development application server'),
        ).toBeInTheDocument()

        fireEvent.change(
            screen.getByRole('searchbox', {
                name: 'Buscar activos',
            }),
            {
                target: {
                    value: 'srv-production-01',
                },
            },
        )

        expect(
            screen.queryByRole('heading', {
                name: 'Detalles del activo',
            }),
        ).not.toBeInTheDocument()

        expect(
            screen.getByText('srv-production-01'),
        ).toBeInTheDocument()
    })

    it('muestra un error si FastAPI devuelve HTTP 500', async () => {
        renderAssets(500)

        expect(
            await screen.findByRole('alert'),
        ).toHaveTextContent(
            'No se pudo cargar el listado de activos.',
        )
    })
})


type TestRole = 'admin' | 'analyst' | 'viewer'

function renderAssetsForRole(role: TestRole) {
  const authFetch = vi.fn<AuthContextValue['authFetch']>()

  authFetch.mockImplementation(async (path, options) => {
    if (path === '/api/v1/assets' && options?.method === 'POST') {
      const values = JSON.parse(String(options.body))

      return {
        ok: true,
        status: 201,
        json: async () => ({
          ...assets[0],
          ...values,
          id: 'asset-created',
        }),
      } as Response
    }

    if (
      path === '/api/v1/assets/asset-development' &&
      options?.method === 'PATCH'
    ) {
      const values = JSON.parse(String(options.body))

      return {
        ok: true,
        status: 200,
        json: async () => ({
          ...assets[0],
          ...values,
        }),
      } as Response
    }

    if (path === '/api/v1/assets') {
      return {
        ok: true,
        status: 200,
        json: async () => assets,
      } as Response
    }

    return {
      ok: false,
      status: 404,
    } as Response
  })

  const session: NonNullable<AuthContextValue['session']> = {
    accessToken: 'test-token',
    user: {
      id: 'test-user',
      email: 'roles@vulnflow.dev',
      full_name: 'Usuario de pruebas',
      role,
      is_active: true,
      created_at: '2026-10-31T12:00:00Z',
      updated_at: '2026-10-31T12:00:00Z',
    },
  }

  render(
    <AuthContext.Provider
      value={{
        session,
        login: vi.fn(),
        logout: vi.fn(),
        authFetch,
      }}
    >
      <AssetsPage />
    </AuthContext.Provider>,
  )

  return authFetch
}

describe('AssetsPage permissions and forms', () => {
  it('mantiene al viewer en modo de consulta', async () => {
    renderAssetsForRole('viewer')

    await screen.findByText('srv-development-01')

    expect(
      screen.queryByRole('button', { name: 'Nuevo activo' }),
    ).not.toBeInTheDocument()

    expect(
      screen.queryByRole('button', { name: 'Editar' }),
    ).not.toBeInTheDocument()

    expect(
      screen.getAllByRole('button', { name: 'Ver detalles' }),
    ).toHaveLength(2)
  })

  it.each(['admin', 'analyst'] as const)(
    'permite crear activos al rol %s',
    async (role) => {
      const authFetch = renderAssetsForRole(role)

      await screen.findByText('srv-development-01')

      fireEvent.click(
        screen.getByRole('button', { name: 'Nuevo activo' }),
      )

      fireEvent.change(
        screen.getByLabelText('Hostname'),
        { target: { value: 'srv-new-01' } },
      )

      fireEvent.change(
        screen.getByLabelText('Dirección IP'),
        { target: { value: '10.0.0.50' } },
      )

      fireEvent.click(
        screen.getByRole('button', { name: 'Guardar activo' }),
      )

      expect(
        await within(screen.getByRole('table')).findByText('srv-new-01'),
      ).toBeInTheDocument()

      const postCall = authFetch.mock.calls.find(
        ([path, options]) =>
          path === '/api/v1/assets' && options?.method === 'POST',
      )

      expect(postCall).toBeDefined()

      const body = JSON.parse(String(postCall?.[1]?.body))

      expect(body).toMatchObject({
        hostname: 'srv-new-01',
        ip_address: '10.0.0.50',
        environment: 'development',
      })
    },
  )

  it.each(['admin', 'analyst'] as const)(
    'permite editar activos al rol %s',
    async (role) => {
      const authFetch = renderAssetsForRole(role)

      await screen.findByText('srv-development-01')

      fireEvent.click(
        screen.getAllByRole('button', { name: 'Editar' })[0],
      )

      expect(
        screen.getByLabelText('Hostname'),
      ).toHaveValue('srv-development-01')

      fireEvent.change(
        screen.getByLabelText('Hostname'),
        { target: { value: 'srv-development-edited' } },
      )

      fireEvent.click(
        screen.getByRole('button', { name: 'Guardar activo' }),
      )

      expect(
        await within(screen.getByRole('table')).findByText(
          'srv-development-edited',
        ),
      ).toBeInTheDocument()

      const patchCall = authFetch.mock.calls.find(
        ([path, options]) =>
          path === '/api/v1/assets/asset-development' &&
          options?.method === 'PATCH',
      )

      expect(patchCall).toBeDefined()

      const body = JSON.parse(String(patchCall?.[1]?.body))

      expect(body.hostname).toBe('srv-development-edited')
    },
  )
})
