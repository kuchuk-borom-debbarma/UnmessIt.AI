import { Link, Outlet, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Database, Search, Layers, BrainCircuit, Combine } from 'lucide-react'

const SECTIONS = [
  { id: 'overview', title: 'The Core Concept', icon: BrainCircuit, path: '/architecture/overview' },
  { id: 'indexing', title: 'The Indexing Engine', icon: Database, path: '/architecture/indexing' },
  { id: 'querying', title: 'The Query Engine', icon: Search, path: '/architecture/querying' },
  { id: 'supporting-systems', title: 'Supporting Systems', icon: Layers, path: '/architecture/supporting-systems' },
  { id: 'integrated', title: 'The Integrated Engine', icon: Combine, path: '/architecture/integrated' },
]

export function ArchitectureShell() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-background text-foreground font-sans relative overflow-x-hidden selection:bg-primary-500/30 selection:text-primary-100">
      {/* Background Glows */}
      <div className="fixed top-[-10%] left-[-10%] w-[50%] h-[50%] bg-primary-500/5 blur-[150px] rounded-full pointer-events-none" />
      <div className="fixed top-[40%] right-[-10%] w-[40%] h-[40%] bg-accent-500/5 blur-[150px] rounded-full pointer-events-none" />

      {/* Top Header - Super Minimal */}
      <header className="fixed top-0 left-0 w-full h-16 border-b border-white/5 bg-background/80 backdrop-blur-xl z-50 flex items-center px-6">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-[0.8rem] bg-gradient-to-tr from-primary-400 to-primary-600 p-[1px] shadow-lg group-hover:shadow-primary-500/25 transition-all group-hover:scale-105 active:scale-95">
            <div className="w-full h-full bg-[#0a0a0b] dark:bg-black rounded-[0.7rem] flex items-center justify-center liquid-glass">
               <img src="/favicon.svg" alt="UnmessIt.AI Logo" className="w-6 h-6 drop-shadow-md" />
            </div>
          </div>
          <span className="font-bold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/70 group-hover:to-white transition-all">
            UnmessIt.AI
          </span>
        </Link>
        <div className="ml-4 pl-4 border-l border-white/10 text-sm font-medium text-muted-foreground flex items-center gap-2">
          Architecture Deep Dive
          <a 
            href="https://github.com/kuchuk-borom-debbarma/UnmessIt.AI" 
            target="_blank" 
            rel="noreferrer"
            className="ml-4 text-xs font-mono bg-white/5 hover:bg-white/10 px-2 py-1 rounded-md border border-white/10 transition-colors"
          >
            Source Code
          </a>
        </div>
      </header>

      {/* Main Content Layout */}
      <div className="flex max-w-[1600px] mx-auto pt-16">
        
        {/* Sticky Sidebar Navigation */}
        <aside className="hidden lg:block w-72 shrink-0 border-r border-white/5 h-[calc(100vh-4rem)] sticky top-16 overflow-y-auto p-6 scrollbar-hide">
          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-4">Architecture Novel</h3>
            {SECTIONS.map((section) => {
              const isActive = location.pathname.includes(section.path)
              const Icon = section.icon
              return (
                <Link
                  key={section.id}
                  to={section.path}
                  className={`flex items-center justify-between text-left px-3 py-3 rounded-xl transition-all duration-300 ${
                    isActive 
                      ? 'bg-primary-500/10 text-primary-400 border border-primary-500/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]' 
                      : 'text-muted-foreground hover:bg-white/5 hover:text-foreground border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon size={18} className={isActive ? 'text-primary-500' : 'text-muted-foreground'} />
                    <span className="text-sm font-bold">{section.title}</span>
                  </div>
                  {isActive && (
                    <motion.div layoutId="activeNav" className="w-1.5 h-1.5 rounded-full bg-primary-500" />
                  )}
                </Link>
              )
            })}
          </div>
        </aside>

        {/* Dynamic Document Area */}
        <main className="flex-1 min-w-0 p-6 lg:p-12 xl:p-16 pb-32">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
