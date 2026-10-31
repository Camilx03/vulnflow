import { describe, expect, it } from 'vitest'

import { getTokenExpiration } from './token'

function createTestToken(payload: unknown): string {
    const encoded = btoa(JSON.stringify(payload))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '')

    return `header.${encoded}.signature`
}

describe('getTokenExpiration', () => {
    it('convierte la fecha de expiración a milisegundos', () => {
        const token = createTestToken({ exp: 1800000000 })

        expect(getTokenExpiration(token)).toBe(1800000000000)
    })

    it('rechaza un JWT sin expiración', () => {
        const token = createTestToken({ sub: 'test-user' })

        expect(getTokenExpiration(token)).toBeNull()
    })

    it('rechaza una expiración que no sea numérica', () => {
        const token = createTestToken({ exp: '1800000000' })

        expect(getTokenExpiration(token)).toBeNull()
    })


    it('rechaza una expiración no finita', () => {
        const payload = btoa('{"exp":1e999}')
        const token = `header.${payload}.signature`

        expect(getTokenExpiration(token)).toBeNull()
    })


    it('rechaza un token malformado', () => {
        expect(getTokenExpiration('invalid-token')).toBeNull()
    })

    it('rechaza un payload que no contiene JSON válido', () => {
        expect(getTokenExpiration('header.bm90LWpzb24.signature')).toBeNull()
    })
})
