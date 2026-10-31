
import { useEffect, useState } from 'react'

import { useAuth } from '../context/AuthContext'
import AssetForm, {
    type AssetFormValues,
} from './AssetForm'

type AssetEnvironment =
    | 'production'
    | 'staging'
    | 'development'
    | 'test'

interface Asset {
    id: string
    hostname: string
    ip_address: string | null
    operating_system: string | null
    environment: AssetEnvironment
    description: string | null
    created_at: string
    updated_at: string
}

const environmentLabels: Record<AssetEnvironment, string> = {
    production: 'Producción',
    staging: 'Preproducción',
    development: 'Desarrollo',
    test: 'Pruebas',
}

function formatDate(value: string): string {
    return new Date(value).toLocaleString('es-ES')
}

export default function AssetsPage() {
    const { authFetch, session } = useAuth()

    const [assets, setAssets] = useState<Asset[]>([])
    const [search, setSearch] = useState('')
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [retry, setRetry] = useState(0)
    const [formMode, setFormMode] = useState<'create' | 'edit' | null>(null)
    const [editingId, setEditingId] = useState<string | null>(null)

    const canManage =
        session?.user.role === 'admin' ||
        session?.user.role === 'analyst'

    useEffect(() => {
        const controller = new AbortController()

        async function loadAssets() {
            try {
                const response = await authFetch('/api/v1/assets', {
                    signal: controller.signal,
                })

                if (!response.ok) {
                    throw new Error(`Error HTTP ${response.status}`)
                }

                const data = (await response.json()) as Asset[]

                if (!controller.signal.aborted) {
                    setAssets(data)
                    setError(null)
                }
            } catch {
                if (!controller.signal.aborted) {
                    setError('No se pudo cargar el listado de activos.')
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false)
                }
            }
        }

        void loadAssets()

        return () => controller.abort()
    }, [authFetch, retry])

    const query = search.trim().toLocaleLowerCase('es')

    const filteredAssets = assets.filter((asset) => {
        const searchable = [
            asset.hostname,
            asset.ip_address ?? '',
            asset.operating_system ?? '',
            environmentLabels[asset.environment],
        ].join(' ').toLocaleLowerCase('es')

        return searchable.includes(query)
    })

    const selectedAsset =
        assets.find((asset) => asset.id === selectedId) ?? null

    function reloadAssets() {
        setLoading(true)
        setError(null)
        setRetry((current) => current + 1)
    }

    async function saveAsset(values: AssetFormValues) {
        if (!canManage || !formMode) {
            throw new Error('No tienes permisos para modificar activos.')
        }

        if (formMode === 'edit' && !editingId) {
            throw new Error('No se ha seleccionado un activo válido.')
        }

        const path =
            formMode === 'edit'
                ? `/api/v1/assets/${editingId}`
                : '/api/v1/assets'

        const response = await authFetch(path, {
            method: formMode === 'edit' ? 'PATCH' : 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(values),
        })

        if (!response.ok) {
            if (response.status === 409) {
                throw new Error('Ya existe un activo con ese hostname.')
            }

            if (response.status === 422) {
                throw new Error('Comprueba el hostname y la dirección IP.')
            }

            if (response.status === 403) {
                throw new Error('No tienes permisos para esta operación.')
            }

            throw new Error(`No se pudo guardar el activo (HTTP ${response.status}).`)
        }

        const savedAsset = (await response.json()) as Asset

        setAssets((current) =>
            formMode === 'create'
                ? [savedAsset, ...current]
                : current.map((asset) =>
                    asset.id === savedAsset.id ? savedAsset : asset,
                ),
        )

        setSearch('')
        setSelectedId(savedAsset.id)
        setFormMode(null)
        setEditingId(null)
    }



    return (
        <section className="assets-page">
            <div className="assets-heading">
                <div>
                    <h1>Assets</h1>
                    <p>Inventario de activos registrados en VulnFlow.</p>
                </div>

                <div className="assets-actions">
                    <button type="button" onClick={reloadAssets}>
                        Actualizar
                    </button>

                    {canManage && (
                        <button
                            type="button"
                            onClick={() => {
                                setEditingId(null)
                                setFormMode('create')
                            }}
                        >
                            Nuevo activo
                        </button>
                    )}
                </div>
            </div>

            <div className="assets-toolbar">
                <label htmlFor="asset-search">Buscar activos</label>
                <input
                    id="asset-search"
                    type="search"
                    placeholder="Hostname, IP, sistema operativo o entorno"
                    value={search}
                    onChange={(event) => {
                        setSearch(event.target.value)
                        setSelectedId(null)
                    }}
                />
            </div>

            {canManage && formMode && (
                <AssetForm
                    key={`${formMode}-${editingId ?? 'new'}`}
                    initial={
                        formMode === 'edit'
                            ? assets.find((asset) => asset.id === editingId) ?? null
                            : null
                    }
                    onSave={saveAsset}
                    onCancel={() => {
                        setFormMode(null)
                        setEditingId(null)
                    }}
                />
            )}
            {loading ? (
                <p role="status">Cargando activos...</p>
            ) : error ? (
                <p role="alert">{error}</p>
            ) : (
                <>
                    <p className="assets-count">
                        Mostrando {filteredAssets.length} de {assets.length} activos
                    </p>

                    {assets.length === 0 ? (
                        <p role="status">
                            Todavía no hay activos registrados.
                        </p>
                    ) : filteredAssets.length === 0 ? (
                        <p role="status">
                            No se encontraron activos con esa búsqueda.
                        </p>
                    ) : (
                        <div className="assets-table-container">
                            <table className="assets-table">
                                <thead>
                                    <tr>
                                        <th scope="col">Hostname</th>
                                        <th scope="col">Dirección IP</th>
                                        <th scope="col">Sistema operativo</th>
                                        <th scope="col">Entorno</th>
                                        <th scope="col">Acciones</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredAssets.map((asset) => (
                                        <tr key={asset.id}>
                                            <td>{asset.hostname}</td>
                                            <td>{asset.ip_address ?? '—'}</td>
                                            <td>{asset.operating_system ?? '—'}</td>
                                            <td>
                                                <span className="assets-environment">
                                                    {environmentLabels[asset.environment]}
                                                </span>
                                            </td>
                                            <td>
                                                <button
                                                    type="button"
                                                    onClick={() => setSelectedId(asset.id)}
                                                >
                                                    Ver detalles
                                                </button>

                                                {canManage && (
                                                    <button
                                                        type="button"
                                                        onClick={() => {
                                                            setEditingId(asset.id)
                                                            setFormMode('edit')
                                                        }}
                                                    >
                                                        Editar
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {selectedAsset && (
                        <section className="assets-details">
                            <div className="assets-details-heading">
                                <h2>Detalles del activo</h2>
                                <button
                                    type="button"
                                    onClick={() => setSelectedId(null)}
                                >
                                    Cerrar
                                </button>
                            </div>

                            <dl>
                                <dt>Hostname</dt>
                                <dd>{selectedAsset.hostname}</dd>

                                <dt>Dirección IP</dt>
                                <dd>{selectedAsset.ip_address ?? 'No indicada'}</dd>

                                <dt>Sistema operativo</dt>
                                <dd>
                                    {selectedAsset.operating_system ?? 'No indicado'}
                                </dd>

                                <dt>Entorno</dt>
                                <dd>
                                    {environmentLabels[selectedAsset.environment]}
                                </dd>

                                <dt>Descripción</dt>
                                <dd>{selectedAsset.description ?? 'Sin descripción'}</dd>

                                <dt>Fecha de creación</dt>
                                <dd>{formatDate(selectedAsset.created_at)}</dd>

                                <dt>Última actualización</dt>
                                <dd>{formatDate(selectedAsset.updated_at)}</dd>
                            </dl>
                        </section>
                    )}
                </>
            )}
        </section>
    )
}
