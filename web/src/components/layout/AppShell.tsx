import { Outlet } from 'react-router-dom'
import { FloatingDock } from './FloatingDock'
import { useVersionCheck } from '../../lib/useVersionCheck'
import { ReleaseHistoryModal } from '../ui/ReleaseHistoryModal'
import { ExternalLink, RefreshCw, UserCircle } from 'lucide-react'
// import { motion } from 'framer-motion'
import { ConfigProvider } from '../../lib/context/ConfigContext'
import { useConfig } from '../../lib/context/useConfig'
import { AlertTriangle, ChevronRight, ServerOff } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { API_BASE, authApi } from '../../lib/api'

const REPOSITORY_URL = 'https://github.com/kuchuk-borom-debbarma/UnmessIt.AI'

function GlobalConnectionBanner() {
  const [isOffline, setIsOffline] = useState(false)

  useEffect(() => {
    let mounted = true
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/health`, { signal: AbortSignal.timeout(3000) })
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
          <p className="text-xs font-medium text-accent-500/80 hidden sm:block">Create one AI config preset before using UnmessIt.AI.</p>
        </div>
      </div>
      <NavLink to="/settings" className="premium-btn premium-btn-primary h-9 px-4">
        Setup Now <ChevronRight size={16} className="ml-2" />
      </NavLink>
    </div>
  )
}

function GlobalUpdateBanner({ updateAvailable, versionInfo }: { updateAvailable: boolean; versionInfo: ReturnType<typeof useVersionCheck>['versionInfo'] }) {
  if (!updateAvailable || !versionInfo) return null

  return (
    <div className="bg-primary-500/10 border-b border-primary-500/20 px-4 py-2 flex items-center justify-between backdrop-blur-xl">
      <div className="flex items-center gap-4">
        <div className="w-8 h-8 rounded-lg bg-primary-500/10 flex items-center justify-center text-primary-500 border border-primary-500/20">
          <RefreshCw size={18} />
        </div>
        <div>
          <h3 className="text-sm font-bold text-primary-500 tracking-tight">Update Available (v{versionInfo.version})</h3>
          <p className="text-xs font-medium text-primary-500/80 hidden sm:block">A new version of UnmessIt.AI is available.</p>
        </div>
      </div>
      <a href={REPOSITORY_URL} target="_blank" rel="noreferrer" className="premium-btn premium-btn-primary h-9 px-4">
        View on GitHub <ExternalLink size={16} className="ml-2" />
      </a>
    </div>
  )
}

export function AppShell({ token, onLogout }: { token: string | null; onLogout: () => void }) {
  const [showChangelog, setShowChangelog] = useState(false)
  const [user, setUser] = useState<{ id: string; identifier: string } | null>(null)
  const { updateAvailable, versionInfo, currentVersion } = useVersionCheck()
  // const location = useLocation()

  useEffect(() => {
    if (!token) {
      setUser(null)
      return
    }
    let mounted = true
    authApi.me(token)
      .then((next) => { if (mounted) setUser(next) })
      .catch(() => { if (mounted) setUser(null) })
    return () => { mounted = false }
  }, [token])

  return (
    <ConfigProvider token={token}>
      {/* 2026 Background FX */}
      <div className="bg-noise" />
      <div className="bg-ambient" />

      {token && (
        <div className="fixed top-0 inset-x-0 z-[60]">
          <div className="mx-auto flex max-w-[1600px] items-center justify-between px-4 py-3 md:px-8">
            <div className="liquid-glass flex min-w-0 items-center gap-3 rounded-lg px-3 py-2">
              <UserCircle size={20} className="shrink-0 text-primary-400" />
              <div className="min-w-0">
                <div className="truncate text-sm font-bold">{user?.identifier || 'Signed in'}</div>
                <div className="truncate text-[11px] font-medium text-muted-foreground">Local workspace</div>
              </div>
            </div>
            <button
              className="liquid-glass inline-flex h-10 items-center gap-2 rounded-lg px-3 text-sm font-bold text-muted-foreground transition-colors hover:text-foreground"
              onClick={() => setShowChangelog(true)}
            >
              v{currentVersion}
              <span className="hidden text-xs font-semibold text-primary-400 sm:inline">Release history</span>
            </button>
          </div>
          <GlobalConnectionBanner />
          <GlobalWarningBanner />
          <GlobalUpdateBanner updateAvailable={updateAvailable} versionInfo={versionInfo} />
        </div>
      )}

      <main className="relative flex-1 flex flex-col min-h-screen w-full max-w-[1600px] mx-auto px-4 md:px-8 pb-28 pt-20 md:pt-24">
        <div className="flex-1 flex flex-col">
          <Outlet />
        </div>
      </main>

      <FloatingDock isAuthenticated={Boolean(token)} onLogout={onLogout} />
      
      <ReleaseHistoryModal 
        isOpen={showChangelog} 
        onClose={() => setShowChangelog(false)} 
        versionInfo={versionInfo} 
        currentVersion={currentVersion} 
        updateAvailable={updateAvailable}
      />
    </ConfigProvider>
  )
}
