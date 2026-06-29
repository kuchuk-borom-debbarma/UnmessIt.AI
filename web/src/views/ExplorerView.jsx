import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { ChevronDown, ChevronRight, Clock, Database, FileText, Link2, PlayCircle, RefreshCw, Tags, Trash2, Trash, RotateCcw, AlertOctagon } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const Pill = ({ children, tone = 'muted' }) => (
  <span className={`detail-pill ${tone}`}>{children}</span>
);

const shortText = (value, fallback = 'Untitled') => {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  return text ? text.slice(0, 90) : fallback;
};

const spanLabel = (span) => `${span.start}-${span.end}`;

const formatJson = (value) => {
  if (!value || (typeof value === 'object' && Object.keys(value).length === 0)) return '';
  return JSON.stringify(value, null, 2);
};

const HighlightedSource = ({ rawText = '', spans = [] }) => {
  const sorted = [...spans].sort((a, b) => a.start - b.start);
  const parts = [];
  let cursor = 0;

  sorted.forEach((span, index) => {
    if (span.start > cursor) {
      parts.push(<span key={`plain-${index}`}>{rawText.slice(cursor, span.start)}</span>);
    }
    parts.push(
      <span key={`hit-${index}`} className="source-highlight">
        {rawText.slice(span.start, span.end)}
      </span>
    );
    cursor = Math.max(cursor, span.end);
  });

  if (cursor < rawText.length) {
    parts.push(<span key="plain-last">{rawText.slice(cursor)}</span>);
  }

  return <div className="evidence-text">{parts}</div>;
};

const TreeRow = ({ depth = 0, active, expandable, expanded, onToggle, onClick, icon, title, meta }) => (
  <button
    className={`seai-tree-row ${active ? 'active' : ''}`}
    style={{ paddingLeft: 12 + depth * 18 }}
    onClick={onClick}
  >
    <span
      className="seai-tree-toggle"
      onClick={(event) => {
        event.stopPropagation();
        if (expandable) onToggle();
      }}
    >
      {expandable ? (expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : <span />}
    </span>
    {icon}
    <span className="seai-tree-title">{title}</span>
    {meta && <span className="seai-tree-meta">{meta}</span>}
  </button>
);

const RawNode = ({ raw, selected, onSelect }) => {
  const [expanded, setExpanded] = useState(true);
  const chunks = raw.source_chunks || [];

  return (
    <div>
      <TreeRow
        active={selected?.kind === 'raw' && selected.raw.id === raw.id}
        expandable={chunks.length > 0}
        expanded={expanded}
        onToggle={() => setExpanded(!expanded)}
        onClick={() => onSelect({ kind: 'raw', raw })}
        icon={<Database size={15} />}
        title={shortText(raw.content, 'Raw input')}
        meta={`${chunks.length} chunks`}
      />
      {expanded && chunks.map((chunk) => (
        <TreeRow
          key={chunk.id}
          depth={1}
          active={selected?.kind === 'chunk' && selected.chunk.id === chunk.id}
          onClick={() => onSelect({ kind: 'chunk', raw, chunk })}
          icon={<FileText size={14} />}
          title={shortText(chunk.summary || chunk.text, 'Source chunk')}
          meta={`${chunk.spans?.length || 0} spans`}
        />
      ))}
    </div>
  );
};

const RecallKeyNode = ({ recallKey, selected, onSelect }) => {
  const [expanded, setExpanded] = useState(true);
  const links = recallKey.links || [];

  return (
    <div>
      <TreeRow
        active={selected?.kind === 'recall_key' && selected.recallKey.id === recallKey.id}
        expandable={links.length > 0}
        expanded={expanded}
        onToggle={() => setExpanded(!expanded)}
        onClick={() => onSelect({ kind: 'recall_key', recallKey })}
        icon={<Tags size={15} />}
        title={recallKey.name}
        meta={`${links.length} links`}
      />
      {expanded && links.map((link) => (
        <TreeRow
          key={link.id}
          depth={1}
          active={selected?.kind === 'recall_link' && selected.link.id === link.id}
          onClick={() => onSelect({ kind: 'recall_link', recallKey, link })}
          icon={<Link2 size={14} />}
          title={shortText(link.source_chunk_summary || link.reason || link.relation, 'Recall link')}
          meta={link.relation_label || link.relation}
        />
      ))}
    </div>
  );
};

const JobNode = ({ job, selected, onSelect }) => (
  <TreeRow
    active={selected?.kind === 'job' && selected.job.id === job.id}
    onClick={() => onSelect({ kind: 'job', job })}
    icon={<Clock size={15} />}
    title={shortText(job.id, 'Ingest job')}
    meta={`${job.status} / ${job.stage}`}
  />
);

export default function ExplorerView() {
  const [rawInputs, setRawInputs] = useState([]);
  const [trashInputs, setTrashInputs] = useState([]);
  const [recallKeys, setRecallKeys] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [totals, setTotals] = useState({ rawInputs: 0, trashInputs: 0, sourceChunks: 0, recallKeys: 0, recallLinks: 0, jobs: 0 });
  const [selected, setSelected] = useState(null);
  const [mode, setMode] = useState('sources');
  const [tab, setTab] = useState('summary');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const rawById = useMemo(() => {
    return Object.fromEntries([...rawInputs, ...trashInputs].map((raw) => [raw.id, raw]));
  }, [rawInputs, trashInputs]);

  useEffect(() => {
    fetchMemory();
  }, []);

  const select = (value) => {
    setSelected(value);
    setTab(value.kind === 'raw' ? 'source' : 'summary');
  };

  const fetchMemory = async () => {
    setLoading(true);
    try {
      const [sourceRes, trashRes, recallRes, jobsRes] = await Promise.all([
        axios.get(`${API_BASE}/dev/seai`),
        axios.get(`${API_BASE}/dev/trash`),
        axios.get(`${API_BASE}/dev/recall`),
        axios.get(`${API_BASE}/dev/ingest_jobs`),
      ]);
      const sourceData = sourceRes.data.data || [];
      const trashData = trashRes.data.data || [];
      const recallData = recallRes.data.data || [];
      const jobData = jobsRes.data.data || [];
      setRawInputs(sourceData);
      setTrashInputs(trashData);
      setRecallKeys(recallData);
      setJobs(jobData);
      setTotals({
        rawInputs: sourceRes.data.total_raw_inputs || 0,
        trashInputs: trashRes.data.total_trash || 0,
        sourceChunks: sourceRes.data.total_source_chunks || 0,
        recallKeys: recallRes.data.total_recall_keys || 0,
        recallLinks: recallRes.data.total_recall_links || 0,
        jobs: jobsRes.data.total_jobs || 0,
      });
      setSelected((current) => refreshSelected(current, sourceData, recallData, jobData));
      setError('');
    } catch (err) {
      console.error(err);
      setError('Failed to fetch memory index');
    } finally {
      setLoading(false);
    }
  };

  const refreshSelected = (current, sourceData, recallData, jobData) => {
    if (!current) return sourceData[0] ? { kind: 'raw', raw: sourceData[0] } : null;
    if (current.kind === 'job') {
      const job = jobData.find((item) => item.id === current.job.id);
      return job ? { kind: 'job', job } : current;
    }
    if (current.kind === 'recall_key') {
      const recallKey = recallData.find((item) => item.id === current.recallKey.id);
      return recallKey ? { kind: 'recall_key', recallKey } : current;
    }
    return current;
  };

  const switchMode = (nextMode) => {
    setMode(nextMode);
    if (nextMode === 'sources') {
      setSelected(rawInputs[0] ? { kind: 'raw', raw: rawInputs[0] } : null);
    } else if (nextMode === 'trash') {
      setSelected(trashInputs[0] ? { kind: 'raw', raw: trashInputs[0] } : null);
    } else if (nextMode === 'recall') {
      setSelected(recallKeys[0] ? { kind: 'recall_key', recallKey: recallKeys[0] } : null);
    } else {
      setSelected(jobs[0] ? { kind: 'job', job: jobs[0] } : null);
    }
  };

  const softDeleteRaw = async (id) => {
    if (!window.confirm("Move this document to the trash? It will be excluded from queries.")) return;
    await axios.delete(`${API_BASE}/dev/raw_inputs/${id}`);
    setSelected(null);
    await fetchMemory();
  };

  const restoreRaw = async (id) => {
    await axios.post(`${API_BASE}/dev/raw_inputs/${id}/restore`);
    setSelected(null);
    await fetchMemory();
  };

  const hardDeleteRaw = async (id) => {
    if (!window.confirm("Permanently delete this document and all its chunks? This cannot be undone.")) return;
    await axios.delete(`${API_BASE}/dev/raw_inputs/${id}/hard`);
    setSelected(null);
    await fetchMemory();
  };

  const resumeJob = async (jobId) => {
    await axios.post(`${API_BASE}/dev/ingest_jobs/${jobId}/resume`);
    await fetchMemory();
  };

  const deleteJob = async (jobId) => {
    if (!window.confirm("Are you sure you want to delete this job and all its checkpoints?")) return;
    await axios.delete(`${API_BASE}/dev/ingest_jobs/${jobId}`);
    setSelected(null);
    await fetchMemory();
  };

  const renderDetail = () => {
    if (!selected) {
      return <div className="empty-state">No memory data indexed yet.</div>;
    }

    if (selected.kind === 'raw') {
      const chunks = selected.raw.source_chunks || [];
      return (
        <>
          <DetailHeader title={selected.raw.deleted_at ? "Trashed Input" : "Raw Input"} pills={[selected.raw.deleted_at ? "Soft Deleted" : `${chunks.length} source chunks`, selected.raw.id]} />
          <Tabs tabs={['source', 'metadata']} tab={tab} setTab={setTab} />
          <div className="detail-body">
            {tab === 'source' && (
              <>
                <div style={{ display: 'flex', gap: '12px', marginBottom: 18 }}>
                  {selected.raw.deleted_at ? (
                    <>
                      <button className="btn btn-primary" onClick={() => restoreRaw(selected.raw.id)}>
                        <RotateCcw size={16} /> Restore
                      </button>
                      <button className="btn" style={{ color: '#ef4444', borderColor: '#ef4444' }} onClick={() => hardDeleteRaw(selected.raw.id)}>
                        <AlertOctagon size={16} /> Hard Delete
                      </button>
                    </>
                  ) : (
                    <button className="btn" style={{ color: '#ef4444', borderColor: '#ef4444' }} onClick={() => softDeleteRaw(selected.raw.id)}>
                      <Trash size={16} /> Move to Trash
                    </button>
                  )}
                </div>
                <div className="evidence-text">{selected.raw.content}</div>
              </>
            )}
            {tab === 'metadata' && (
              <Metadata rows={[
                ['id', selected.raw.id],
                ['job_id', selected.raw.job_id],
                ['created_at', selected.raw.created_at],
                ['deleted_at', selected.raw.deleted_at || ''],
              ]} />
            )}
          </div>
        </>
      );
    }

    if (selected.kind === 'chunk') {
      const { raw, chunk } = selected;
      return (
        <>
          <DetailHeader title="Source Chunk" pills={[`${chunk.spans?.length || 0} spans`, chunk.id]} />
          <Tabs tabs={['summary', 'source', 'metadata']} tab={tab} setTab={setTab} />
          <div className="detail-body">
            {tab === 'summary' && (
              <>
                <h3 className="detail-heading">Summary</h3>
                <div className="evidence-text">{chunk.summary || 'No summary.'}</div>
                <h3 className="detail-heading" style={{ marginTop: 18 }}>Chunk Text</h3>
                <div className="evidence-text">{chunk.text}</div>
                <div className="detail-meta">
                  {chunk.source_time && <Pill><Clock size={12} /> {chunk.source_time}</Pill>}
                  {(chunk.spans || []).map((span) => <Pill key={spanLabel(span)}>{spanLabel(span)}</Pill>)}
                </div>
              </>
            )}
            {tab === 'source' && <HighlightedSource rawText={raw.content} spans={chunk.spans || []} />}
            {tab === 'metadata' && (
              <Metadata rows={[
                ['id', chunk.id],
                ['raw_input_id', chunk.raw_input_id],
                ['source_time', chunk.source_time || ''],
                ['created_at', chunk.created_at],
                ['metadata', formatJson(chunk.metadata)],
              ]} />
            )}
          </div>
        </>
      );
    }

    if (selected.kind === 'recall_key') {
      const { recallKey } = selected;
      return (
        <>
          <DetailHeader title="Recall Key" pills={[recallKey.kind, `${recallKey.link_count} links`, recallKey.id]} />
          <Tabs tabs={['summary', 'links', 'metadata']} tab={tab} setTab={setTab} />
          <div className="detail-body">
            {tab === 'summary' && (
              <>
                <h3 className="detail-heading">Summary</h3>
                <div className="evidence-text">{recallKey.summary || 'No summary.'}</div>
                <div className="detail-meta">
                  {recallKey.kind_label && <Pill tone="green">{recallKey.kind_label}</Pill>}
                  {(recallKey.aliases || []).map((alias) => <Pill key={alias} tone="blue">{alias}</Pill>)}
                  {recallKey.latest_link_time && <Pill><Clock size={12} /> {recallKey.latest_link_time}</Pill>}
                </div>
              </>
            )}
            {tab === 'links' && <RecallLinkList links={recallKey.links || []} />}
            {tab === 'metadata' && (
              <Metadata rows={[
                ['id', recallKey.id],
                ['kind', recallKey.kind],
                ['kind_label', recallKey.kind_label || ''],
                ['aliases', (recallKey.aliases || []).join(', ')],
                ['created_at', recallKey.created_at],
                ['updated_at', recallKey.updated_at],
                ['metadata', formatJson(recallKey.metadata)],
              ]} />
            )}
          </div>
        </>
      );
    }

    if (selected.kind === 'job') {
      const { job } = selected;
      const canResume = ['failed', 'waiting_retry'].includes(job.status);
      return (
        <>
          <DetailHeader title="Ingest Job" pills={[job.status, job.stage, job.id]} />
          <Tabs tabs={['summary', 'metadata']} tab={tab} setTab={setTab} />
          <div className="detail-body">
            {tab === 'summary' && (
              <>
                <div className="detail-meta">
                  <Pill tone={job.status === 'complete' ? 'green' : 'muted'}>{job.status}</Pill>
                  <Pill>{job.stage}</Pill>
                  <Pill>{job.attempt_count || 0} attempts</Pill>
                </div>
                {job.error && (
                  <>
                    <h3 className="detail-heading" style={{ marginTop: 18 }}>Error</h3>
                    <div className="evidence-text" style={{ color: '#ef4444' }}>{job.error}</div>
                  </>
                )}
                <div style={{ display: 'flex', gap: '12px', marginTop: 18 }}>
                  {canResume && (
                    <button className="btn btn-primary" onClick={() => resumeJob(job.id)}>
                      <PlayCircle size={16} /> Resume Job
                    </button>
                  )}
                  <button className="btn" style={{ color: '#ef4444', borderColor: '#ef4444' }} onClick={() => deleteJob(job.id)}>
                    <Trash2 size={16} /> Delete Job
                  </button>
                </div>
                <h3 className="detail-heading" style={{ marginTop: 18 }}>Counts</h3>
                <div className="evidence-text">{formatJson(job.metadata) || 'No counts yet.'}</div>
              </>
            )}
            {tab === 'metadata' && (
              <Metadata rows={[
                ['id', job.id],
                ['content_hash', job.content_hash],
                ['raw_input_id', job.raw_input_id || ''],
                ['status', job.status],
                ['stage', job.stage],
                ['attempt_count', String(job.attempt_count || 0)],
                ['next_run_at', job.next_run_at || ''],
                ['error', job.error || ''],
                ['created_at', job.created_at],
                ['updated_at', job.updated_at],
                ['metadata', formatJson(job.metadata)],
              ]} />
            )}
          </div>
        </>
      );
    }

    const { recallKey, link } = selected;
    const raw = rawById[link.raw_input_id];
    return (
      <>
        <DetailHeader title="Recall Link" pills={[recallKey.name, link.relation_label || link.relation, link.id]} />
        <Tabs tabs={['summary', 'source', 'metadata']} tab={tab} setTab={setTab} />
        <div className="detail-body">
          {tab === 'summary' && (
            <>
              <h3 className="detail-heading">Reason</h3>
              <div className="evidence-text">{link.reason || 'No reason.'}</div>
              <div className="detail-meta">
                <Pill tone="green">{link.relation}</Pill>
                {link.relation_label && <Pill>{link.relation_label}</Pill>}
                <Pill>{Math.round((link.confidence || 0) * 100)}%</Pill>
                {(link.event_time || link.time_label) && <Pill><Clock size={12} /> {link.event_time || link.time_label}</Pill>}
              </div>
              <h3 className="detail-heading" style={{ marginTop: 18 }}>Linked Source Chunk</h3>
              <div className="evidence-text">{link.source_chunk_text || link.source_chunk_summary}</div>
            </>
          )}
          {tab === 'source' && (
            raw
              ? <HighlightedSource rawText={raw.content} spans={link.source_chunk_spans || []} />
              : <div className="evidence-text">{link.source_chunk_text || 'Source chunk unavailable.'}</div>
          )}
          {tab === 'metadata' && (
            <Metadata rows={[
              ['id', link.id],
              ['recall_key_id', link.recall_key_id],
              ['source_chunk_id', link.source_chunk_id],
              ['raw_input_id', link.raw_input_id || ''],
              ['relation', link.relation],
              ['relation_label', link.relation_label || ''],
              ['confidence', String(link.confidence)],
              ['event_time', link.event_time || ''],
              ['time_label', link.time_label || ''],
              ['created_at', link.created_at],
              ['metadata', formatJson(link.metadata)],
              ['source_chunk_metadata', formatJson(link.source_chunk_metadata)],
            ]} />
          )}
        </div>
      </>
    );
  };

  return (
    <div className="view-container explorer-layout" style={{ display: 'flex', gap: '24px', height: '100%', maxWidth: 'none' }}>
      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div className="panel-header">
          <h2><Database size={20} className="text-blue" /> Memory Explorer</h2>
          <div className="detail-meta">
            {mode === 'sources' ? (
              <>
                <Pill>{totals.rawInputs} raw inputs</Pill>
                <Pill>{totals.sourceChunks} source chunks</Pill>
              </>
            ) : mode === 'trash' ? (
              <Pill>{totals.trashInputs} trashed inputs</Pill>
            ) : mode === 'recall' ? (
              <>
                <Pill>{totals.recallKeys} recall keys</Pill>
                <Pill>{totals.recallLinks} links</Pill>
              </>
            ) : (
              <Pill>{totals.jobs} jobs</Pill>
            )}
            <button className="icon-btn" onClick={fetchMemory} title="Refresh memory index">
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
        <Tabs tabs={['sources', 'trash', 'recall', 'jobs']} tab={mode} setTab={switchMode} />
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
          {loading ? (
            <div className="empty-state">Loading memory index...</div>
          ) : error ? (
            <div className="empty-state" style={{ color: '#ef4444' }}>{error}</div>
          ) : mode === 'sources' && rawInputs.length === 0 ? (
            <div className="empty-state">No source chunks indexed yet.</div>
          ) : mode === 'trash' && trashInputs.length === 0 ? (
            <div className="empty-state">Trash is empty.</div>
          ) : mode === 'recall' && recallKeys.length === 0 ? (
            <div className="empty-state">No recall keys indexed yet.</div>
          ) : mode === 'jobs' && jobs.length === 0 ? (
            <div className="empty-state">No ingest jobs yet.</div>
          ) : mode === 'sources' ? (
            rawInputs.map((raw) => (
              <RawNode key={raw.id} raw={raw} selected={selected} onSelect={select} />
            ))
          ) : mode === 'trash' ? (
            trashInputs.map((raw) => (
              <RawNode key={raw.id} raw={raw} selected={selected} onSelect={select} />
            ))
          ) : mode === 'recall' ? (
            recallKeys.map((recallKey) => (
              <RecallKeyNode key={recallKey.id} recallKey={recallKey} selected={selected} onSelect={select} />
            ))
          ) : (
            jobs.map((job) => (
              <JobNode key={job.id} job={job} selected={selected} onSelect={select} />
            ))
          )}
        </div>
      </div>

      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {renderDetail()}
      </div>
    </div>
  );
}

const DetailHeader = ({ title, pills }) => (
  <div className="panel-header">
    <h2><FileText size={18} className="text-yellow" /> {title}</h2>
    <div className="detail-meta">
      {pills.filter(Boolean).map((pill) => <Pill key={pill}>{pill}</Pill>)}
    </div>
  </div>
);

const Tabs = ({ tabs, tab, setTab }) => (
  <div className="segmented-tabs" style={{ padding: '0 20px 14px' }}>
    {tabs.map((item) => (
      <button key={item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>
        {item}
      </button>
    ))}
  </div>
);

const RecallLinkList = ({ links }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
    {links.map((link) => (
      <div key={link.id} className="span-card">
        <div className="detail-meta">
          <Pill tone="green">{link.relation}</Pill>
          {link.relation_label && <Pill>{link.relation_label}</Pill>}
          <Pill>{Math.round((link.confidence || 0) * 100)}%</Pill>
          {(link.event_time || link.time_label) && <Pill>{link.event_time || link.time_label}</Pill>}
        </div>
        <div className="evidence-text" style={{ color: 'var(--text-primary)' }}>
          {link.source_chunk_summary || link.reason || 'No source summary.'}
        </div>
      </div>
    ))}
  </div>
);

const Metadata = ({ rows }) => (
  <div className="metadata-grid">
    {rows.map(([label, value]) => (
      <React.Fragment key={label}>
        <div>{label}</div>
        <div className="evidence-text">{value || ''}</div>
      </React.Fragment>
    ))}
  </div>
);
