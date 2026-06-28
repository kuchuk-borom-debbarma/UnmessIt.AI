import React, { useState } from 'react'
import axios from 'axios'
import { Trash2 } from 'lucide-react'

export default function DatabaseControls() {
  const [status, setStatus] = useState('idle')

  const handleWipeDatabase = async () => {
    if (!window.confirm("Are you absolutely sure? This will delete all SEAI memories and source documents permanently.")) {
      return
    }

    setStatus('wiping')
    try {
      await axios.delete('http://localhost:8000/dev/facts')
      setStatus('success')
      setTimeout(() => setStatus('idle'), 3000)
    } catch (err) {
      console.error(err)
      setStatus('error')
    }
  }

  return (
    <div className="view-container">
      <div className="view-header">
        <h2>Database Controls</h2>
        <p>Manage local SQLite and vector storage.</p>
      </div>

      <div className="glass-panel" style={{ padding: '24px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
        <h3 style={{ color: '#ef4444', marginBottom: 12 }}>Danger Zone</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
          Completely wipe local memory. This deletes raw inputs, source chunks, recall keys, and recall links.
          It also clears durable ingest jobs, checkpoints, recall lookup indexes, and the vector store.
          This action cannot be undone.
        </p>
        
        <button 
          className="btn btn-danger" 
          onClick={handleWipeDatabase}
          disabled={status === 'wiping'}
        >
          <Trash2 size={18} />
          {status === 'wiping' ? 'Wiping...' : 'Wipe Database Completely'}
        </button>

        {status === 'success' && (
          <div style={{ marginTop: 16, color: '#4ade80' }}>
            Database wiped successfully!
          </div>
        )}
      </div>
    </div>
  )
}
