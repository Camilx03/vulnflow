
import { useEffect, useState } from 'react'

import { useAuth } from '../context/AuthContext'

interface DashboardStats {
    total_assets: number
    total_vulnerabilities: number
    affected_assets: number
    unassigned_vulnerabilities: number
    active_vulnerabilities: number
    by_severity: Record<string, number>
    by_status: Record<string, number>
}

const severities = [
    { key: 'critical', label: 'Crítica' },
    { key: 'high', label: 'Alta' },
    { key: 'medium', label: 'Media' },
    { key: 'low', label: 'Baja' },
    { key: 'info', label: 'Informativa' },
]

const statuses = [
    { key: 'open', label: 'Abierta' },
    { key: 'in_progress', label: 'En progreso' },
    { key: 'resolved', label: 'Resuelta' },
    { key: 'accepted_risk', label: 'Riesgo aceptado' },
    { key: 'false_positive', label: 'Falso positivo' },
]

interface DistributionProps {
    title: string
    values: Record<string, number>
    categories: { key: string; label: string }[]
    total: number
}

function Distribution({
    title,
    values,
    categories,
    total,
}: DistributionProps) {
    return (
        <section className="dashboard-panel">
            <h2>{title}</h2>

            <ul className="dashboard-distribution">
                {categories.map(({ key, label }) => {
                    const count = values[key] ?? 0
                    const percentage = total > 0 ? (count / total) * 100 : 0

                    return (
                        <li key={key}>
                            <div className="dashboard-distribution-label">
                                <span>{label}</span>
                                <strong>{count}</strong>
                            </div>

                            <progress
                                value={count}
                                max={Math.max(total, 1)}
                                aria-label={`${label}: ${count} (${percentage.toFixed(1)}%)`}
                            />
                        </li>
                    )
                })}
            </ul>
        </section>
    )
}

export default function DashboardPage() {
    const { authFetch } = useAuth()

    const [stats, setStats] = useState<DashboardStats | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const controller = new AbortController()

        async function loadDashboard() {
            try {
                const response = await authFetch('/api/v1/dashboard/stats', {
                    signal: controller.signal,
                })

                if (!response.ok) {
                    throw new Error(`Error HTTP ${response.status}`)
                }

                const data = (await response.json()) as DashboardStats

                if (!controller.signal.aborted) {
                    setStats(data)
                }
            } catch {
                if (!controller.signal.aborted) {
                    setError('No se pudieron cargar los indicadores del dashboard.')
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false)
                }
            }
        }

        void loadDashboard()

        return () => controller.abort()
    }, [authFetch])

    if (loading) {
        return <p role="status">Cargando indicadores...</p>
    }

    if (error || !stats) {
        return (
            <p role="alert">
                {error ?? 'No hay datos disponibles.'}
            </p>
        )
    }

    const metrics = [
        { label: 'Activos totales', value: stats.total_assets },
        { label: 'Vulnerabilidades', value: stats.total_vulnerabilities },
        { label: 'Vulnerabilidades activas', value: stats.active_vulnerabilities },
        { label: 'Activos afectados', value: stats.affected_assets },
        { label: 'Sin asignar', value: stats.unassigned_vulnerabilities },
    ]

    return (
        <section className="dashboard">
            <h1>Dashboard</h1>
            <p className="dashboard-description">
                Resumen actual del estado de seguridad de los activos.
            </p>

            <div className="dashboard-metrics">
                {metrics.map((metric) => (
                    <article className="dashboard-metric" key={metric.label}>
                        <span>{metric.label}</span>
                        <strong>{metric.value}</strong>
                    </article>
                ))}
            </div>

            {stats.total_vulnerabilities === 0 && (
                <p className="dashboard-empty">
                    Todavía no hay vulnerabilidades registradas.
                </p>
            )}

            <div className="dashboard-panels">
                <Distribution
                    title="Vulnerabilidades por gravedad"
                    values={stats.by_severity}
                    categories={severities}
                    total={stats.total_vulnerabilities}
                />

                <Distribution
                    title="Vulnerabilidades por estado"
                    values={stats.by_status}
                    categories={statuses}
                    total={stats.total_vulnerabilities}
                />
            </div>
        </section>
    )
}
