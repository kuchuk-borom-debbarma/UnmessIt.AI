import { useEffect, useState, useCallback } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api'
import type { Preset } from '../api'
import { ConfigContext } from './ConfigContextCore'

export function ConfigProvider({ children, token }: { children: ReactNode; token: string | null }) {
  const [hasActivePreset, setHasActivePreset] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(Boolean(token))

  const checkConfig = useCallback(async () => {
    if (!token) {
      setHasActivePreset(null)
      setLoading(false)
      return
    }

    try {
      const presets = await api<Preset[]>('/configs/presets', { token })
      setHasActivePreset(presets.some((p) => p.is_active === 1))
    } catch {
      setHasActivePreset(false)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    void checkConfig()
  }, [checkConfig])

  return (
    <ConfigContext.Provider value={{ hasActivePreset, loading, checkConfig }}>
      {children}
    </ConfigContext.Provider>
  )
}
