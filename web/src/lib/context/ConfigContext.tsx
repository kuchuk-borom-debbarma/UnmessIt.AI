import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api'
import type { Preset } from '../api'

type ConfigContextType = {
  hasActivePreset: boolean | null
  loading: boolean
  checkConfig: () => Promise<void>
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined)

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

export function useConfig() {
  const context = useContext(ConfigContext)
  if (context === undefined) {
    throw new Error('useConfig must be used within a ConfigProvider')
  }
  return context
}
