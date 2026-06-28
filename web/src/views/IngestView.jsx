import React, { useState } from 'react'
import axios from 'axios'
import { Send, Loader } from 'lucide-react'

export default function IngestView() {
  const [text, setText] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | success | error
  const [jobId, setJobId] = useState(null)

  const handleIngest = async () => {
    if (!text.trim()) return
    
    setStatus('loading')
    try {
      const response = await axios.post('http://localhost:8000/ingest/', { text })
      setJobId(response.data.job_id)
      setStatus('success')
      setText('')
    } catch (err) {
      console.error(err)
      setStatus('error')
    }
  }

  return (
    <div className="view-container">
      <div className="view-header">
        <h2>Ingest Notes</h2>
        <p>Save notes as source chunks with recall keys and links.</p>
      </div>

      <div className="glass-panel" style={{ padding: '24px' }}>
        <textarea 
          className="input-field" 
          rows="12" 
          placeholder="Start typing your thoughts..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        ></textarea>
        
        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button 
            className="btn btn-primary" 
            onClick={handleIngest} 
            disabled={status === 'loading' || !text.trim()}
          >
            {status === 'loading' ? <Loader className="pulse" size={18} /> : <Send size={18} />}
            {status === 'loading' ? 'Processing in background...' : 'Ingest'}
          </button>
          
          {status === 'success' && (
            <span className="status-badge success">
              <div className="pulse" style={{ background: 'currentColor' }}></div>
              Job {jobId?.split('-')[0]} queued successfully
            </span>
          )}
          {status === 'error' && (
            <span className="status-badge" style={{ color: '#ef4444', background: 'rgba(239,68,68,0.1)' }}>
              Error connecting to server
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
