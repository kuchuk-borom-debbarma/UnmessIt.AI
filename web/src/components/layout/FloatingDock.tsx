import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { FileText, Bot, Activity, LogOut, LogIn, UserPlus } from 'lucide-react'
import { cn } from '../../lib/utils'
import { authApi } from '../../lib/api'

const dockItems = [
  { path: '/notes', label: 'Notes', icon: FileText },
  { path: '/ask', label: 'Ask AI', icon: Bot },
  { path: '/jobs', label: 'Jobs', icon: Activity },
]

export function FloatingDock({ token, onLogout }: { token: string | null; onLogout: () => void }) {
  const isAuthenticated = Boolean(token)
  const [username, setUsername] = useState<string | null>(null)

  useEffect(() => {
    if (token) {
      authApi.me(token)
        .then(res => setUsername(res.identifier))
        .catch(() => setUsername(null))
    } else {
      setUsername(null)
    }
  }, [token])

  return (
    <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 flex h-16 items-center justify-between w-[calc(100%-2rem)] max-w-4xl px-2 py-2 liquid-glass rounded-2xl gap-2">
      {isAuthenticated ? (
        <>
          {dockItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => cn(
                'nav-pill w-full flex-1 group px-2',
                isActive && 'active'
              )}
              aria-label={item.label}
              title={item.label}
            >
              {({ isActive }) => (
                <div className="relative z-10 flex h-11 items-center justify-center gap-2.5">
                  <item.icon size={18} className={cn("transition-colors shrink-0", isActive ? "text-primary-400" : "")} />
                  <span className={cn("text-[11px] font-bold uppercase tracking-widest leading-none mt-0.5 whitespace-nowrap", isActive ? "text-primary-400" : "opacity-50 group-hover:opacity-100 transition-opacity", "hidden md:block")}>
                    {item.label}
                  </span>
                </div>
              )}
            </NavLink>
          ))}
          <div className="nav-pill w-full flex-1 group relative cursor-default px-4 h-11 flex items-center justify-center bg-white/5 border border-white/5">
            <span className="text-sm font-bold text-primary-400 truncate max-w-[150px] whitespace-nowrap">
              {username || 'Profile'}
            </span>
          </div>
          <button
            onClick={onLogout}
            className="nav-pill shrink-0 hover:text-red-400 hover:bg-red-500/10 h-11 w-11 flex items-center justify-center"
            aria-label="Logout"
            title="Logout"
          >
            <LogOut size={18} />
          </button>
        </>
      ) : (
        <nav className="flex items-center gap-2 w-full justify-center">
          <NavLink
            to="/login"
            className="guest-nav-link"
            aria-label="Sign in"
          >
            <LogIn size={16} />
            <span>Login</span>
          </NavLink>
          <NavLink
            to="/signup"
            className="guest-nav-link guest-nav-primary"
            aria-label="Sign up"
          >
            <UserPlus size={16} />
            <span>Sign up</span>
          </NavLink>
        </nav>
      )}
    </div>
  )
}
