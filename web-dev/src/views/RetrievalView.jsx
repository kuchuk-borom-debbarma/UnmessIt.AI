import React, { useState } from 'react'
import axios from 'axios'
import { Search, Loader, Bot, FileText, X } from 'lucide-react'

// A small component to cleanly truncate long arrays
const TruncatedList = ({ items, maxStart = 3, maxEnd = 2, renderItem }) => {
  if (!items || items.length === 0) return <span style={{ color: 'var(--text-tertiary)' }}>none</span>;
  if (items.length <= maxStart + maxEnd) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {items.map((item, idx) => <div key={idx}>{renderItem ? renderItem(item, idx) : item}</div>)}
      </div>
    );
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      {items.slice(0, maxStart).map((item, idx) => <div key={`start-${idx}`}>{renderItem ? renderItem(item, idx) : item}</div>)}
      <div style={{ color: 'var(--text-tertiary)', paddingLeft: '8px', fontSize: '12px' }}>... ({items.length - maxStart - maxEnd} more items) ...</div>
      {items.slice(-maxEnd).map((item, idx) => <div key={`end-${idx}`}>{renderItem ? renderItem(item, idx) : item}</div>)}
    </div>
  );
};

// Modular component for the complex retrieval trace
const RetrievalTraceDetails = ({ trace }) => {
  if (!trace) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '12px' }}>
      
      {/* Global Metadata */}
      <div className="span-card">
        <h4 style={{ fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '4px' }}>Global Stats</h4>
        <div className="metadata-grid" style={{ gridTemplateColumns: '120px 1fr' }}>
          <div>mode</div><div>{trace.mode || 'unknown'}</div>
          <div>sub-queries</div><div>{trace.sub_query_count || 1}</div>
          <div>extracted subjects</div>
          <div>
            <TruncatedList items={trace.extracted_subjects} maxStart={3} maxEnd={1} />
          </div>
          <div>citations</div><div>{trace.citation_count || 0}</div>
          <div>context sizes</div>
          <div>
            before: {trace.context_chars_before_packing || 0}c 
            → after: {trace.context_chars_after_packing || 0}c 
            (saved: {trace.context_chars_saved || 0}c)
          </div>
        </div>
      </div>

      {/* Sub-Query Breakdowns */}
      {trace.sub_query_traces && trace.sub_query_traces.length > 0 && (
        <div className="span-card">
          <h4 style={{ fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '4px' }}>Sub-Query Traces</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {trace.sub_query_traces.map((sqt, idx) => (
              <div key={idx} style={{ background: 'rgba(0,0,0,0.1)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.02)' }}>
                <div style={{ fontWeight: 'bold', color: 'var(--primary-color)', marginBottom: '8px', fontSize: '13px' }}>"{sqt.sub_query}"</div>
                <div className="metadata-grid" style={{ gridTemplateColumns: '120px 1fr', fontSize: '12px' }}>
                   <div>lexical matches</div><div>{sqt.lexical_source_chunk_count || 0} chunks</div>
                   <div>vector matches</div>
                   <div>
                     <TruncatedList items={sqt.vector_source_chunk_ids} maxStart={2} maxEnd={1} />
                   </div>
                   <div>recall keys</div>
                   <div>
                     <TruncatedList items={sqt.recall_keys} maxStart={3} maxEnd={1} renderItem={(key) => `${key.name} (id: ${key.id.substring(0,8)}...)`} />
                   </div>
                   <div>linked chunks</div><div>{sqt.linked_source_chunk_count || 0} chunks</div>
                   <div>merged chunks</div><div>{sqt.source_chunk_count || 0} total found</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ranked Source Chunks */}
      {(trace.ranked_source_chunk_ids || []).length > 0 && (
        <div className="span-card">
          <h4 style={{ fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '4px' }}>Ranked & Selected Evidence ({trace.ranked_source_chunk_ids.length})</h4>
          <TruncatedList 
             items={trace.ranked_source_chunk_ids} 
             maxStart={4} 
             maxEnd={2} 
             renderItem={(id) => {
                 const reasons = trace.chunk_score_reasons?.[id] || [];
                 const snippets = trace.selected_snippet_counts?.[id] || 0;
                 return (
                   <div style={{ display: 'flex', flexDirection: 'column', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                     <span style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{id}</span>
                     <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                       snippets packed: {snippets} | reasons: {reasons.join(', ') || 'none'}
                     </span>
                   </div>
                 );
             }} 
          />
        </div>
      )}
    </div>
  );
};

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
  
  const [progressEvents, setProgressEvents] = useState([])

  const handleQuery = async () => {
    if (!query.trim()) return
    
    setStatus('loading')
    setAnswer(null)
    setCitations([])
    setSourceChunks([])
    setRetrievalTrace(null)
    setSelectedCitation(null)
    setProgressEvents([])
    
    const clientId = crypto.randomUUID()
    const eventSource = new EventSource(`http://localhost:8000/api/retrieval/events/${clientId}`)
    
    eventSource.addEventListener('progress', (e) => {
        try {
            const data = JSON.parse(e.data)
            setProgressEvents(prev => [...prev, data.message])
        } catch (err) {
            console.error("Failed to parse progress event", err)
        }
    })
    
    try {
      const response = await axios.post('http://localhost:8000/api/retrieval/query', { query, client_id: clientId })
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
    } finally {
      eventSource.close()
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
            
            {(status === 'loading' || progressEvents.length > 0) && (
              <div style={{ 
                  marginTop: '16px', 
                  background: 'rgba(0,0,0,0.4)', 
                  border: '1px solid rgba(255,255,255,0.05)', 
                  borderRadius: '6px', 
                  padding: '12px',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  color: 'var(--text-tertiary)',
                  maxHeight: '150px',
                  overflowY: 'auto',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px'
              }}>
                {progressEvents.map((msg, idx) => (
                    <div key={idx} style={{ display: 'flex', gap: '8px' }}>
                        <span style={{ color: 'var(--primary-color)' }}>&gt;</span>
                        <span>{msg}</span>
                    </div>
                ))}
                {status === 'loading' && (
                    <div style={{ display: 'flex', gap: '8px', opacity: 0.7, animation: 'pulse 2s infinite' }}>
                        <span style={{ color: 'var(--primary-color)' }}>&gt;</span>
                        <span>_</span>
                    </div>
                )}
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
                    Retrieval Trace Details
                  </summary>
                  <RetrievalTraceDetails trace={retrievalTrace} />
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
