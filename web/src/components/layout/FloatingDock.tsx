import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileText, Bot, Activity, Settings, LogOut, Moon, Sun, LogIn, UserPlus } from 'lucide-react'
import { cn } from '../../lib/utils'
import { useTheme } from '../../lib/context/ThemeContext'

const dockItems = [
  { path: '/notes', label: 'Notes', icon: FileText },
  { path: '/ask', label: 'Ask AI', icon: Bot },
  { path: '/jobs', label: 'Jobs', icon: Activity },
  { path: '/settings', label: 'Config', icon: Settings },
]

export function FloatingDock({ isAuthenticated, onLogout }: { isAuthenticated: boolean; onLogout: () => void }) {
  const { theme, setTheme } = useTheme()

  return (
    <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 flex h-16 items-center gap-2 p-2 liquid-glass rounded-2xl">
      {/* Brand Icon */}
      <NavLink to="/" className="w-11 h-11 rounded-lg flex items-center justify-center bg-foreground/5 hover:bg-foreground/10 transition-colors">
        <img src="/favicon.svg" alt="UnmessIt.AI" className="w-6 h-6 object-contain" />
      </NavLink>

      <div className="w-px h-8 bg-border/50 mx-1" />

      {isAuthenticated ? (
        <nav className="flex items-center gap-1">
          {dockItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => cn(
                'nav-pill group',
                isActive && 'active'
              )}
              aria-label={item.label}
              title={item.label}
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="dock-indicator"
                      className="absolute inset-0 rounded-lg bg-primary-500/10 border border-primary-500/20"
                      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                    />
                  )}
                  <div className="relative z-10 flex h-11 w-11 flex-col items-center justify-center gap-0.5">
                    <item.icon size={20} className={cn("transition-colors", isActive ? "text-primary-400" : "")} />
                    <span className={cn("text-[8px] font-bold uppercase tracking-wider hidden md:block leading-none", isActive ? "text-primary-400" : "opacity-0 group-hover:opacity-100 transition-opacity")}>
                      {item.label}
                    </span>
                  </div>
                </>
              )}
            </NavLink>
          ))}
        </nav>
      ) : (
        <nav className="flex items-center gap-2">
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

      <div className="w-px h-8 bg-border/50 mx-1" />

      {/* Actions */}
      <div className="flex items-center gap-1 pr-2">
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="nav-pill"
          aria-label="Toggle Theme"
          title="Toggle Theme"
        >
          {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </button>
        {isAuthenticated && (
          <button
            onClick={onLogout}
            className="nav-pill hover:text-red-400 hover:bg-red-500/10"
            aria-label="Logout"
            title="Logout"
          >
            <LogOut size={20} />
          </button>
        )}
      </div>
    </div>
  )
}
