
import {
    act,
    cleanup,
    fireEvent,
    render,
    screen,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider } from './AuthProvider'
import { useAuth } from './AuthContext'
import type { AuthSession } from '../services/auth'

function createSession(): AuthSession {
    const expiresAt = Math.floor(Date.now() / 1000) + 60

    const payload = btoa(JSON.stringify({ exp: expiresAt }))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '')

    return {
        accessToken: `header.${payload}.signature`,
        user: {
            id: 'test-user-id',
            email: 'test@vulnflow.dev',
            full_name: 'Test User',
            role: 'viewer',
            is_active: true,
            created_at: '2026-10-31T12:00:00Z',
            updated_at: '2026-10-31T12:00:00Z',
        },
    }
}

function TestConsumer() {
    const { session, login, logout, authFetch } = useAuth()

    return (
        <div>
            <p data-testid="auth-status">
                {session ? 'Autenticado' : 'Sin sesión'}
            </p>

            <button type="button" onClick={() => login(createSession())}>
                Iniciar
            </button>

            <button type="button" onClick={logout}>
                Salir
            </button>

            <button
                type="button"
                onClick={() => {
                    void authFetch('/api/v1/dashboard/stats')
                }}
            >
                Consultar API
            </button>
        </div>
    )
}

function renderProvider() {
    return render(
        <AuthProvider>
            <TestConsumer />
        </AuthProvider>,
    )
}

afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllGlobals()
})

describe('AuthProvider', () => {
    it('permite iniciar y cerrar sesión', () => {
        renderProvider()

        expect(screen.getByTestId('auth-status')).toHaveTextContent(
            'Sin sesión',
        )

        fireEvent.click(screen.getByRole('button', { name: 'Iniciar' }))

        expect(screen.getByTestId('auth-status')).toHaveTextContent(
            'Autenticado',
        )

        fireEvent.click(screen.getByRole('button', { name: 'Salir' }))

        expect(screen.getByTestId('auth-status')).toHaveTextContent(
            'Sin sesión',
        )
    })

    it('cierra automáticamente una sesión caducada', () => {
        vi.useFakeTimers()
        vi.setSystemTime(new Date('2026-10-31T12:00:00Z'))

        renderProvider()

        fireEvent.click(screen.getByRole('button', { name: 'Iniciar' }))

        expect(screen.getByTestId('auth-status')).toHaveTextContent(
            'Autenticado',
        )

        act(() => {
            vi.advanceTimersByTime(61_000)
        })

        expect(screen.getByTestId('auth-status')).toHaveTextContent(
            'Sin sesión',
        )
    })

    it('cierra sesión cuando la API devuelve HTTP 401', async () => {
        const fetchMock = vi.fn().mockResolvedValue({ status: 401 })
        vi.stubGlobal('fetch', fetchMock)

        renderProvider()

        fireEvent.click(screen.getByRole('button', { name: 'Iniciar' }))

        await act(async () => {
            fireEvent.click(
                screen.getByRole('button', { name: 'Consultar API' }),
            )
        })

        expect(fetchMock).toHaveBeenCalledOnce()

        expect(screen.getByTestId('auth-status')).toHaveTextContent(
            'Sin sesión',
        )
    })

    it('mantiene la sesión cuando la API devuelve HTTP 403', async () => {
        const fetchMock = vi.fn().mockResolvedValue({ status: 403 })
        vi.stubGlobal('fetch', fetchMock)

        renderProvider()

        fireEvent.click(screen.getByRole('button', { name: 'Iniciar' }))

        await act(async () => {
            fireEvent.click(
                screen.getByRole('button', { name: 'Consultar API' }),
            )
        })

        expect(screen.getByTestId('auth-status')).toHaveTextContent(
            'Autenticado',
        )
    })

    it('mantiene la sesión ante un error HTTP 500', async () => {
        const fetchMock = vi.fn().mockResolvedValue({ status: 500 })
        vi.stubGlobal('fetch', fetchMock)

        renderProvider()

        fireEvent.click(screen.getByRole('button', { name: 'Iniciar' }))

        await act(async () => {
            fireEvent.click(
                screen.getByRole('button', { name: 'Consultar API' }),
            )
        })

        expect(screen.getByTestId('auth-status')).toHaveTextContent(
            'Autenticado',
        )
    })
})
