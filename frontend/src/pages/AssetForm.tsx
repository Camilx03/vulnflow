
import { useState, type FormEvent } from 'react'

export type AssetEnvironment =
  | 'production'
  | 'staging'
  | 'development'
  | 'test'

export interface AssetFormValues {
  hostname: string
  ip_address: string | null
  operating_system: string | null
  environment: AssetEnvironment
  description: string | null
}

interface AssetFormProps {
  initial?: AssetFormValues | null
  onSave: (values: AssetFormValues) => Promise<void>
  onCancel: () => void
}

export default function AssetForm({
  initial,
  onSave,
  onCancel,
}: AssetFormProps) {
  const [hostname, setHostname] = useState(initial?.hostname ?? '')
  const [ipAddress, setIpAddress] = useState(initial?.ip_address ?? '')
  const [operatingSystem, setOperatingSystem] = useState(
    initial?.operating_system ?? '',
  )
  const [environment, setEnvironment] = useState<AssetEnvironment>(
    initial?.environment ?? 'development',
  )
  const [description, setDescription] = useState(
    initial?.description ?? '',
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (saving) return

    setSaving(true)
    setError(null)

    try {
      await onSave({
        hostname: hostname.trim().toLowerCase(),
        ip_address: ipAddress.trim() || null,
        operating_system: operatingSystem.trim() || null,
        environment,
        description: description.trim() || null,
      })
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'No se pudo guardar el activo.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="asset-form-panel">
      <h2>{initial ? 'Editar activo' : 'Nuevo activo'}</h2>

      <form className="asset-form" onSubmit={(event) => {
        void handleSubmit(event)
      }}>
        <label htmlFor="asset-hostname">Hostname</label>
        <input
          id="asset-hostname"
          value={hostname}
          onChange={(event) => setHostname(event.target.value)}
          required
          maxLength={255}
        />

        <label htmlFor="asset-ip">Dirección IP</label>
        <input
          id="asset-ip"
          value={ipAddress}
          onChange={(event) => setIpAddress(event.target.value)}
          placeholder="192.168.1.10"
        />

        <label htmlFor="asset-os">Sistema operativo</label>
        <input
          id="asset-os"
          value={operatingSystem}
          onChange={(event) => setOperatingSystem(event.target.value)}
          maxLength={120}
        />

        <label htmlFor="asset-environment">Entorno</label>
        <select
          id="asset-environment"
          value={environment}
          onChange={(event) =>
            setEnvironment(event.target.value as AssetEnvironment)
          }
        >
          <option value="production">Producción</option>
          <option value="staging">Preproducción</option>
          <option value="development">Desarrollo</option>
          <option value="test">Pruebas</option>
        </select>

        <label htmlFor="asset-description">Descripción</label>
        <textarea
          id="asset-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
        />

        {error && <p role="alert" className="auth-error">{error}</p>}

        <div className="asset-form-actions">
          <button type="submit" disabled={saving}>
            {saving ? 'Guardando...' : 'Guardar activo'}
          </button>
          <button type="button" onClick={onCancel} disabled={saving}>
            Cancelar
          </button>
        </div>
      </form>
    </section>
  )
}
