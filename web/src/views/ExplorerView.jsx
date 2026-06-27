import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { ChevronDown, ChevronRight, Database, FileText, Hash, Layers, RefreshCw, ShieldCheck } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const Pill = ({ children, tone = 'muted' }) => (
  <span className={`detail-pill ${tone}`}>{children}</span>
);

const spanLabel = (span) => `${span.start}-${span.end}`;

const spanText = (rawText, spans = []) => (
  spans.map((span) => rawText.slice(span.start, span.end)).join('\n...\n')
);

const HighlightedSource = ({ rawText, spans = [] }) => {
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

const RawNode = ({ raw, selected, setSelected }) => {
  const [expanded, setExpanded] = useState(true);
  const isActive = selected?.kind === 'raw' && selected.raw.id === raw.id;

  return (
    <div>
      <TreeRow
        active={isActive}
        expandable={raw.episodes.length > 0}
        expanded={expanded}
        onToggle={() => setExpanded(!expanded)}
        onClick={() => setSelected({ kind: 'raw', raw })}
        icon={<Database size={15} />}
        title={raw.content.slice(0, 80) || 'Raw input'}
        meta={`${raw.episodes.length} episodes`}
      />
      {expanded && raw.episodes.map((episode) => (
        <EpisodeNode
          key={episode.id}
          raw={raw}
          episode={episode}
          selected={selected}
          setSelected={setSelected}
        />
      ))}
    </div>
  );
};

const EpisodeNode = ({ raw, episode, selected, setSelected }) => {
  const [expanded, setExpanded] = useState(true);
  const isActive = selected?.kind === 'episode' && selected.episode.id === episode.id;

  return (
    <div>
      <TreeRow
        depth={1}
        active={isActive}
        expandable={episode.atoms.length > 0}
        expanded={expanded}
        onToggle={() => setExpanded(!expanded)}
        onClick={() => setSelected({ kind: 'episode', raw, episode })}
        icon={<Layers size={15} />}
        title={episode.summary || episode.text.slice(0, 80)}
        meta={`${episode.spans.length} spans`}
      />
      {expanded && episode.atoms.map((atom) => (
        <TreeRow
          key={atom.id}
          depth={2}
          active={selected?.kind === 'atom' && selected.atom.id === atom.id}
          onClick={() => setSelected({ kind: 'atom', raw, episode, atom })}
          icon={<FileText size={14} />}
          title={atom.content}
          meta={atom.atom_role}
        />
      ))}
    </div>
  );
};

export default function ExplorerView() {
  const [rawInputs, setRawInputs] = useState([]);
  const [totals, setTotals] = useState({ episodes: 0, atoms: 0 });
  const [selected, setSelected] = useState(null);
  const [tab, setTab] = useState('summary');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchSEAI();
  }, []);

  const select = (value) => {
    setSelected(value);
    setTab(value.kind === 'raw' ? 'source' : 'summary');
  };

  const fetchSEAI = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/dev/seai`);
      const data = res.data.data || [];
      setRawInputs(data);
      setTotals({ episodes: res.data.total_episodes || 0, atoms: res.data.total_atoms || 0 });
      setSelected((current) => current || (data[0] ? { kind: 'raw', raw: data[0] } : null));
      setError('');
    } catch (err) {
      console.error(err);
      setError('Failed to fetch SEAI index');
    } finally {
      setLoading(false);
    }
  };

  const renderDetail = () => {
    if (!selected) {
      return <div className="empty-state">No SEAI memories indexed yet.</div>;
    }

    if (selected.kind === 'raw') {
      return (
        <>
          <DetailHeader title="Raw Input" pills={[`${selected.raw.episodes.length} episodes`, selected.raw.id]} />
          <div className="detail-body">
            <div className="evidence-text">{selected.raw.content}</div>
          </div>
        </>
      );
    }

    if (selected.kind === 'episode') {
      const { raw, episode } = selected;
      return (
        <>
          <DetailHeader
            title="Episode"
            pills={[`${episode.spans.length} spans`, `${episode.atoms.length} atoms`, episode.id]}
          />
          <Tabs tabs={['summary', 'spans', 'atoms', 'source', 'metadata']} tab={tab} setTab={setTab} />
          <div className="detail-body">
            {tab === 'summary' && (
              <>
                <h3 className="detail-heading">Summary</h3>
                <div className="evidence-text">{episode.summary}</div>
                <h3 className="detail-heading">Episode Text</h3>
                <div className="evidence-text">{episode.text}</div>
              </>
            )}
            {tab === 'spans' && (
              <SpanList rawText={raw.content} spans={episode.spans} />
            )}
            {tab === 'atoms' && (
              <AtomList rawText={raw.content} atoms={episode.atoms} />
            )}
            {tab === 'source' && (
              <HighlightedSource rawText={raw.content} spans={episode.spans} />
            )}
            {tab === 'metadata' && (
              <Metadata rows={[
                ['episode_id', episode.id],
                ['raw_input_id', episode.raw_input_id],
                ['created_at', episode.created_at],
              ]} />
            )}
          </div>
        </>
      );
    }

    const { raw, episode, atom } = selected;
    return (
      <>
        <DetailHeader
          title="Atom"
          pills={[atom.atom_role, `${Math.round(atom.confidence * 100)}% confidence`, atom.id]}
        />
        <Tabs tabs={['summary', 'evidence', 'source', 'metadata']} tab={tab} setTab={setTab} />
        <div className="detail-body">
          {tab === 'summary' && (
            <>
              <h3 className="detail-heading">Content</h3>
              <div className="evidence-text">{atom.content}</div>
              <div className="detail-meta">
                <Pill><ShieldCheck size={12} /> {atom.atom_role}</Pill>
                <Pill><Hash size={12} /> {Math.round(atom.confidence * 100)}%</Pill>
                {atom.annotations.map((item) => <Pill key={item} tone="blue">{item}</Pill>)}
              </div>
            </>
          )}
          {tab === 'evidence' && (
            <SpanList rawText={raw.content} spans={atom.evidence_spans} />
          )}
          {tab === 'source' && (
            <HighlightedSource rawText={raw.content} spans={atom.evidence_spans} />
          )}
          {tab === 'metadata' && (
            <Metadata rows={[
              ['atom_id', atom.id],
              ['episode_id', episode.id],
              ['raw_input_id', atom.raw_input_id],
              ['created_at', atom.created_at],
            ]} />
          )}
        </div>
      </>
    );
  };

  return (
    <div className="view-container explorer-layout" style={{ display: 'flex', gap: '24px', height: '100%' }}>
      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div className="panel-header">
          <h2><Database size={20} className="text-blue" /> SEAI Index</h2>
          <div className="detail-meta">
            <Pill>{totals.episodes} episodes</Pill>
            <Pill>{totals.atoms} atoms</Pill>
            <button className="icon-btn" onClick={fetchSEAI} title="Refresh SEAI index">
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
          {loading ? (
            <div className="empty-state">Loading SEAI index...</div>
          ) : error ? (
            <div className="empty-state" style={{ color: '#ef4444' }}>{error}</div>
          ) : rawInputs.length === 0 ? (
            <div className="empty-state">No SEAI memories indexed yet.</div>
          ) : (
            rawInputs.map((raw) => (
              <RawNode key={raw.id} raw={raw} selected={selected} setSelected={select} />
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
      {pills.map((pill) => <Pill key={pill}>{pill}</Pill>)}
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

const SpanList = ({ rawText, spans }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
    {spans.map((span, index) => (
      <div key={`${span.start}-${span.end}-${index}`} className="span-card">
        <Pill>{spanLabel(span)}</Pill>
        <div className="evidence-text">{rawText.slice(span.start, span.end)}</div>
      </div>
    ))}
  </div>
);

const AtomList = ({ rawText, atoms }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
    {atoms.map((atom) => (
      <div key={atom.id} className="span-card">
        <div className="detail-meta">
          <Pill tone={atom.atom_role === 'relation' ? 'green' : 'blue'}>{atom.atom_role}</Pill>
          <Pill>{Math.round(atom.confidence * 100)}%</Pill>
          {atom.annotations.map((item) => <Pill key={item}>{item}</Pill>)}
        </div>
        <div className="evidence-text" style={{ color: 'var(--text-primary)' }}>{atom.content}</div>
        <div className="evidence-text">{spanText(rawText, atom.evidence_spans)}</div>
      </div>
    ))}
  </div>
);

const Metadata = ({ rows }) => (
  <div className="metadata-grid">
    {rows.map(([label, value]) => (
      <React.Fragment key={label}>
        <div>{label}</div>
        <div>{value}</div>
      </React.Fragment>
    ))}
  </div>
);
