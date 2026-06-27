import React from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { Database, FolderTree, Send, Search } from 'lucide-react'
import IngestView from './views/IngestView'
import ExplorerView from './views/ExplorerView'
import DatabaseControls from './views/DatabaseControls'
import RetrievalView from './views/RetrievalView'

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <aside className="sidebar">
          <h1>UnmessIt.AI</h1>
          <nav className="nav-links">
            <NavLink to="/" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
              <Send size={18} /> Ingest Journal
            </NavLink>
            <NavLink to="/explorer" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
              <FolderTree size={18} /> SEAI Explorer
            </NavLink>
            <NavLink to="/query" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
              <Search size={18} /> Ask AI
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
              <Database size={18} /> Database
            </NavLink>
          </nav>
        </aside>
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<IngestView />} />
            <Route path="/explorer" element={<ExplorerView />} />
            <Route path="/query" element={<RetrievalView />} />
            <Route path="/settings" element={<DatabaseControls />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
