import { useEffect, useState, useCallback } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api'
import type { StageConfig } from '../api'
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
      const [stages] = await Promise.all([
        api<StageConfig>('/api/v1/configs/stages', { token }),
      ])
      setHasActivePreset(
        stages.llm_configs.length > 0 && stages.embedding_configs.length > 0
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
