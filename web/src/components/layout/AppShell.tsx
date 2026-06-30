import { Outlet } from 'react-router-dom'
import { FloatingDock } from './FloatingDock'
// import { motion } from 'framer-motion'
import { ConfigProvider, useConfig } from '../../lib/context/ConfigContext'
import { AlertTriangle, ChevronRight, ServerOff } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { API_BASE } from '../../lib/api'

function GlobalConnectionBanner() {
  const [isOffline, setIsOffline] = useState(false)

  useEffect(() => {
    let mounted = true
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) })
        if (mounted) setIsOffline(!res.ok)
      } catch {
        if (mounted) setIsOffline(true)
      }
    }
    
    checkHealth()
    const interval = setInterval(checkHealth, 5000)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  if (!isOffline) return null

  return (
    <div className="bg-red-500 text-white px-4 py-2 shadow-lg font-space">
      <div className="flex items-center justify-center gap-3">
        <ServerOff size={18} />
        <span className="font-bold tracking-tight">Server Disconnected</span>
        <span className="text-white/80 text-sm hidden sm:block ml-2">UnmessIt.AI cannot reach the backend. Please check your connection or start the server.</span>
      </div>
    </div>
  )
}

function GlobalWarningBanner() {
  const { hasActivePreset, loading } = useConfig()
  
  if (loading || hasActivePreset !== false) return null
  
  return (
    <div className="bg-accent-500/10 border-b border-accent-500/20 px-4 py-2 flex items-center justify-between backdrop-blur-xl">
      <div className="flex items-center gap-4">
        <div className="w-8 h-8 rounded-lg bg-accent-500/10 flex items-center justify-center text-accent-500 border border-accent-500/20">
          <AlertTriangle size={18} />
        </div>
        <div>
          <h3 className="text-sm font-bold text-accent-500 tracking-tight">Missing AI Configuration</h3>
          <p className="text-xs font-medium text-accent-500/80 hidden sm:block">Configure an AI preset before using UnmessIt.AI.</p>
        </div>
      </div>
      <NavLink to="/settings" className="premium-btn premium-btn-primary h-9 px-4">
        Setup Now <ChevronRight size={16} className="ml-2" />
      </NavLink>
    </div>
  )
}

export function AppShell({ token, onLogout }: { token: string | null; onLogout: () => void }) {
  // const location = useLocation()

  return (
    <ConfigProvider token={token}>
      {/* 2026 Background FX */}
      <div className="bg-noise" />
      <div className="bg-ambient" />

      {token && (
        <div className="fixed top-0 inset-x-0 z-[60]">
          <GlobalConnectionBanner />
          <GlobalWarningBanner />
        </div>
      )}

      <main className="relative flex-1 flex flex-col min-h-screen w-full max-w-[1600px] mx-auto px-4 md:px-8 pb-28 pt-20 md:pt-24">
        <div className="flex-1 flex flex-col">
          <Outlet />
        </div>
      </main>

      <FloatingDock isAuthenticated={Boolean(token)} onLogout={onLogout} />
    </ConfigProvider>
  )
}
