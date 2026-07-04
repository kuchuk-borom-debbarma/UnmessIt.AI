import { useEffect, useState, useCallback } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api'
import type { Preset, RotationConfig, StageConfig } from '../api'
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
      const [presets, rotation, stages] = await Promise.all([
        api<Preset[]>('/api/v1/configs/presets', { token }),
        api<RotationConfig>('/api/v1/configs/rotation', { token }),
        api<StageConfig>('/api/v1/configs/stages', { token }),
      ])
      setHasActivePreset(
        presets.some((p) => p.is_active === 1)
        || (rotation.enabled && rotation.preset_ids.length >= 2)
        || (stages.llm_configs.length > 0 && stages.embedding_configs.length > 0),
      )
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
