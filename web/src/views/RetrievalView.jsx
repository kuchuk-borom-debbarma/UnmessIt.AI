import React, { useState } from 'react'
import axios from 'axios'
import { Search, Loader, Bot, FileText, X } from 'lucide-react'

export default function RetrievalView() {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | success | error
  const [answer, setAnswer] = useState(null)
  const [citations, setCitations] = useState([])
  const [sourceChunks, setSourceChunks] = useState([])
  const [retrievalTrace, setRetrievalTrace] = useState(null)
  
  const [selectedCitation, setSelectedCitation] = useState(null)
  const [rawInput, setRawInput] = useState(null)
  const [loadingRaw, setLoadingRaw] = useState(false)

  const handleQuery = async () => {
    if (!query.trim()) return
    
    setStatus('loading')
    setAnswer(null)
    setCitations([])
    setSourceChunks([])
    setRetrievalTrace(null)
    setSelectedCitation(null)
    
    try {
      const response = await axios.post('http://localhost:8000/api/retrieval/query', { query })
      if (typeof response.data === 'object' && response.data.answer) {
         setAnswer(response.data.answer)
         setCitations(response.data.citations || [])
         setSourceChunks(response.data.source_chunks || [])
         setRetrievalTrace(response.data.retrieval_trace || null)
      } else {
         setAnswer(response.data) // fallback
      }
      setStatus('success')
    } catch (err) {
      console.error(err)
      setStatus('error')
    }
  }

  const handleViewSource = async (citation) => {
    setSelectedCitation(citation)
    if (!citation.source_input_id) {
        setRawInput("No source document associated with this citation.")
        return
    }
    setLoadingRaw(true)
    try {
      const res = await axios.get(`http://localhost:8000/dev/raw_inputs/${citation.source_input_id}`)
      setRawInput(res.data.data.content)
    } catch (err) {
      console.error(err)
      setRawInput("Failed to load original document.")
    } finally {
      setLoadingRaw(false)
    }
  }

  const renderHighlightedSource = () => {
    if (!rawInput || !selectedCitation) return null

    let before = rawInput;
    let highlighted = "";
    let after = "";
    
    // Attempt highlighting using indices
    if (selectedCitation.start_char !== undefined && selectedCitation.start_char !== null && selectedCitation.end_char !== undefined && selectedCitation.end_char !== null) {
        before = rawInput.substring(0, selectedCitation.start_char)
        highlighted = rawInput.substring(selectedCitation.start_char, selectedCitation.end_char)
        after = rawInput.substring(selectedCitation.end_char)
    } else if (selectedCitation.raw_text) {
        // Fallback to searching for the raw text string
        const idx = rawInput.indexOf(selectedCitation.raw_text)
        if (idx !== -1) {
            before = rawInput.substring(0, idx)
            highlighted = rawInput.substring(idx, idx + selectedCitation.raw_text.length)
            after = rawInput.substring(idx + selectedCitation.raw_text.length)
        }
    }

    // Provide an anchor we can scroll to after render
    if (highlighted) {
        setTimeout(() => {
          const el = document.getElementById('highlighted-source')
          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }, 100)
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
        {/* Extracted Snippets Panel */}
        <div style={{ 
            background: 'rgba(255, 255, 255, 0.02)', 
            border: '1px solid rgba(255, 255, 255, 0.05)', 
            borderRadius: '8px', 
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
        }}>
            <h3 style={{ fontSize: '14px', color: 'var(--primary-color)', margin: 0 }}>Extracted Information</h3>
            
            <div style={{ borderLeft: '2px solid rgba(255,255,255,0.1)', paddingLeft: '12px' }}>
                <strong style={{ display: 'block', fontSize: '11px', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Source Chunk</strong>
                <div style={{ color: 'var(--text-secondary)' }}>{selectedCitation.raw_text || "N/A"}</div>
            </div>
            
            <div style={{ borderLeft: '2px solid var(--primary-color)', paddingLeft: '12px' }}>
                <strong style={{ display: 'block', fontSize: '11px', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Chunk Summary</strong>
                <div style={{ color: '#fff' }}>{selectedCitation.cleaned_text || "N/A"}</div>
            </div>
        </div>

        {/* Full Document highlighting */}
        <div>
            <h3 style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '12px' }}>Full Source Document</h3>
            <div style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.02)' }}>
              {before}
              {highlighted && (
                <span id="highlighted-source" style={{ backgroundColor: 'rgba(250, 204, 21, 0.3)', color: '#fff', borderRadius: '2px', padding: '0 2px' }}>
                    {highlighted}
                </span>
              )}
              {after}
            </div>
        </div>
      </div>
    )
  }

  return (
    <div className="view-container" style={{ display: 'flex', gap: '24px', height: '100%', flexDirection: 'row' }}>
      
      {/* Left Panel: Chat Interface */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
          <div className="view-header">
            <h2>Ask AI</h2>
            <p>Query your ingested thoughts and let the AI search your knowledge base.</p>
          </div>

          <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
            <div style={{ display: 'flex', gap: '16px' }}>
              <input
                type="text"
                className="input-field"
                style={{ flex: 1, padding: '12px 16px' }}
                placeholder="E.g., What did I decide about the project architecture?"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
              />
              
              <button 
                className="btn btn-primary" 
                onClick={handleQuery} 
                disabled={status === 'loading' || !query.trim()}
              >
                {status === 'loading' ? <Loader className="pulse" size={18} /> : <Search size={18} />}
                Search
              </button>
            </div>
            
            {status === 'error' && (
              <div style={{ marginTop: '16px', color: '#ef4444' }}>
                Error connecting to server. Is the API running?
              </div>
            )}
          </div>
          
          {answer && (
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: 'var(--text-secondary)' }}>
                <Bot size={20} /> AI Response
              </h3>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', marginBottom: '24px' }}>
                {answer}
              </div>
              
              {citations && citations.length > 0 && (
                  <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.05)', paddingTop: '16px' }}>
                      <h4 style={{ fontSize: '14px', color: 'var(--text-tertiary)', marginBottom: '12px' }}>Sources</h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {citations.map((cit, idx) => (
                              <button 
                                key={idx}
                                onClick={() => handleViewSource(cit)}
                                style={{ 
                                    textAlign: 'left', 
                                    background: 'rgba(255, 255, 255, 0.03)', 
                                    border: `1px solid ${selectedCitation === cit ? 'var(--primary-color)' : 'rgba(255, 255, 255, 0.05)'}`,
                                    padding: '12px', 
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                    color: 'var(--text-secondary)',
                                    fontSize: '13px'
                                }}
                              >
                                  <strong>[{idx + 1}]</strong> <em>"{cit.exact_quote}"</em>
                                  {cit.cleaned_text && (
                                    <div style={{ marginTop: '8px', color: 'var(--text-tertiary)' }}>{cit.cleaned_text}</div>
                                  )}
                              </button>
                          ))}
                      </div>
                  </div>
              )}

              {sourceChunks && sourceChunks.length > 0 && (
                <details style={{ borderTop: '1px solid rgba(255, 255, 255, 0.05)', marginTop: '16px', paddingTop: '16px' }}>
                  <summary style={{ color: 'var(--text-tertiary)', cursor: 'pointer', fontSize: '14px' }}>
                    Source Chunks
                  </summary>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
                    {sourceChunks.map((chunk, idx) => (
                      <div key={chunk.id} className="span-card">
                        <div className="detail-meta">
                          <span className="detail-pill">chunk {idx + 1}</span>
                          <span className="detail-pill">{chunk.id}</span>
                        </div>
                        <div style={{ color: 'var(--text-secondary)', lineHeight: 1.5 }}>{chunk.summary || 'No summary'}</div>
                        <div className="evidence-text">{chunk.text}</div>
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {retrievalTrace && (
                <details style={{ borderTop: '1px solid rgba(255, 255, 255, 0.05)', marginTop: '16px', paddingTop: '16px' }}>
                  <summary style={{ color: 'var(--text-tertiary)', cursor: 'pointer', fontSize: '14px' }}>
                    Retrieval Trace
                  </summary>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '12px' }}>
                    <div className="metadata-grid">
                      <div>mode</div>
                      <div>{retrievalTrace.mode || 'unknown'}</div>
                      <div>source chunks</div>
                      <div>{retrievalTrace.source_chunk_count || 0}</div>
                      <div>lexical matches</div>
                      <div>{retrievalTrace.lexical_source_chunk_count || 0}</div>
                      <div>linked chunks</div>
                      <div>{retrievalTrace.linked_source_chunk_count || 0}</div>
                      <div>citations</div>
                      <div>{retrievalTrace.citation_count || 0}</div>
                      <div>context before</div>
                      <div>{retrievalTrace.context_chars_before_packing || 0} chars</div>
                      <div>context after</div>
                      <div>{retrievalTrace.context_chars_after_packing || 0} chars</div>
                      <div>context saved</div>
                      <div>{retrievalTrace.context_chars_saved || 0} chars</div>
                    </div>
                    {(retrievalTrace.ranked_source_chunk_ids || []).length > 0 && (
                      <div className="span-card">
                        <div className="detail-meta">
                          <span className="detail-pill">ranked chunks</span>
                          <span className="detail-pill">{retrievalTrace.ranked_source_chunk_ids.length}</span>
                        </div>
                        <div className="evidence-text">
                          {retrievalTrace.ranked_source_chunk_ids.join(', ')}
                        </div>
                      </div>
                    )}
                    {retrievalTrace.selected_snippet_counts && (
                      <div className="span-card">
                        <div className="detail-meta">
                          <span className="detail-pill">packed snippets</span>
                        </div>
                        <div className="evidence-text">
                          {Object.entries(retrievalTrace.selected_snippet_counts)
                            .map(([chunkId, count]) => `${chunkId}: ${count}`)
                            .join('\n')}
                        </div>
                      </div>
                    )}
                    {retrievalTrace.chunk_score_reasons && (
                      <div className="span-card">
                        <div className="detail-meta">
                          <span className="detail-pill">score reasons</span>
                        </div>
                        <div className="evidence-text">
                          {Object.entries(retrievalTrace.chunk_score_reasons)
                            .map(([chunkId, reasons]) => `${chunkId}: ${(reasons || []).join(', ')}`)
                            .join('\n')}
                        </div>
                      </div>
                    )}
                    {(retrievalTrace.recall_keys || []).length > 0 && (
                      <div className="span-card">
                        <div className="detail-meta">
                          <span className="detail-pill">recall keys</span>
                          <span className="detail-pill">{retrievalTrace.recall_key_count || 0}</span>
                        </div>
                        <div className="evidence-text">
                          {retrievalTrace.recall_keys.map((key) => key.name).join(', ')}
                        </div>
                      </div>
                    )}
                  </div>
                </details>
              )}
            </div>
          )}
      </div>

      {/* Right Panel: Source Viewer */}
      {selectedCitation && (
        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '20px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2 style={{ fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <FileText size={18} className="text-yellow" /> Source Document
                    </h2>
                    <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                        Doc ID: {selectedCitation.source_input_id || 'Unknown'}
                    </p>
                </div>
                <button onClick={() => setSelectedCitation(null)} style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer' }}>
                    <X size={18} />
                </button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px', fontFamily: 'monospace', fontSize: '13px', lineHeight: '1.6' }}>
                {loadingRaw ? (
                    <div style={{ color: 'var(--text-tertiary)' }}>Loading document...</div>
                ) : (
                    renderHighlightedSource()
                )}
            </div>
        </div>
      )}
    </div>
  )
}
