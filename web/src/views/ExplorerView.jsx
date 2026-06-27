import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { ChevronDown, ChevronRight, Clock, Database, FileText, Hash, Layers, RefreshCw, ShieldCheck, Tags } from 'lucide-react';

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

const SubjectNode = ({ subject, selected, setSelected }) => {
  const [expanded, setExpanded] = useState(true);
  const isActive = selected?.kind === 'subject' && selected.subject.id === subject.id;

  return (
    <div>
      <TreeRow
        active={isActive}
        expandable={subject.links.length > 0}
        expanded={expanded}
        onToggle={() => setExpanded(!expanded)}
        onClick={() => setSelected({ kind: 'subject', subject })}
        icon={<Tags size={15} />}
        title={subject.name}
        meta={`${subject.link_count} links`}
      />
      {expanded && subject.links.map((link) => (
        <TreeRow
          key={link.id}
          depth={1}
          active={selected?.kind === 'subject_link' && selected.link.id === link.id}
          onClick={() => setSelected({ kind: 'subject_link', subject, link })}
          icon={<Clock size={14} />}
          title={link.atom_content || link.episode_summary || link.reason || link.relation}
          meta={link.relation}
        />
      ))}
    </div>
  );
};

export default function ExplorerView() {
  const [rawInputs, setRawInputs] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [totals, setTotals] = useState({ episodes: 0, atoms: 0 });
  const [subjectTotals, setSubjectTotals] = useState({ subjects: 0, links: 0 });
  const [selected, setSelected] = useState(null);
  const [mode, setMode] = useState('seai');
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
      const [res, subjectRes] = await Promise.all([
        axios.get(`${API_BASE}/dev/seai`),
        axios.get(`${API_BASE}/dev/subjects`),
      ]);
      const data = res.data.data || [];
      const subjectData = subjectRes.data.data || [];
      setRawInputs(data);
      setSubjects(subjectData);
      setTotals({ episodes: res.data.total_episodes || 0, atoms: res.data.total_atoms || 0 });
      setSubjectTotals({
        subjects: subjectRes.data.total_subjects || 0,
        links: subjectRes.data.total_links || 0,
      });
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

    if (selected.kind === 'subject') {
      const { subject } = selected;
      return (
        <>
          <DetailHeader title="Memory Subject" pills={[subject.kind, `${subject.link_count} links`, subject.id]} />
          <div className="detail-body">
            <h3 className="detail-heading">Summary</h3>
            <div className="evidence-text">{subject.summary || 'No summary.'}</div>
            <div className="detail-meta">
              {subject.aliases.map((alias) => <Pill key={alias} tone="blue">{alias}</Pill>)}
              {subject.latest_link_time && <Pill><Clock size={12} /> {subject.latest_link_time}</Pill>}
            </div>
            <h3 className="detail-heading" style={{ marginTop: 18 }}>Timeline Links</h3>
            <SubjectLinkList links={subject.links} />
          </div>
        </>
      );
    }

    if (selected.kind === 'subject_link') {
      const { subject, link } = selected;
      return (
        <>
          <DetailHeader title="Subject Link" pills={[subject.name, link.relation, link.id]} />
          <div className="detail-body">
            <h3 className="detail-heading">Evidence Hint</h3>
            <div className="evidence-text">{link.atom_content || link.episode_summary || link.reason}</div>
            <h3 className="detail-heading">Reason</h3>
            <div className="evidence-text">{link.reason || 'No reason.'}</div>
            <Metadata rows={[
              ['subject_id', link.subject_id],
              ['raw_input_id', link.raw_input_id],
              ['episode_id', link.episode_id],
              ['atom_id', link.atom_id || ''],
              ['relation', link.relation],
              ['confidence', String(link.confidence)],
              ['event_time', link.event_time || ''],
              ['time_label', link.time_label || ''],
              ['created_at', link.created_at],
            ]} />
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
          <h2><Database size={20} className="text-blue" /> Explorer</h2>
          <div className="detail-meta">
            {mode === 'seai' ? (
              <>
                <Pill>{totals.episodes} episodes</Pill>
                <Pill>{totals.atoms} atoms</Pill>
              </>
            ) : (
              <>
                <Pill>{subjectTotals.subjects} subjects</Pill>
                <Pill>{subjectTotals.links} links</Pill>
              </>
            )}
            <button className="icon-btn" onClick={fetchSEAI} title="Refresh SEAI index">
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
        <Tabs tabs={['seai', 'subjects']} tab={mode} setTab={(nextMode) => {
          setMode(nextMode);
          setSelected(nextMode === 'seai'
            ? (rawInputs[0] ? { kind: 'raw', raw: rawInputs[0] } : null)
            : (subjects[0] ? { kind: 'subject', subject: subjects[0] } : null));
        }} />
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
          {loading ? (
            <div className="empty-state">Loading SEAI index...</div>
          ) : error ? (
            <div className="empty-state" style={{ color: '#ef4444' }}>{error}</div>
          ) : mode === 'seai' && rawInputs.length === 0 ? (
            <div className="empty-state">No SEAI memories indexed yet.</div>
          ) : mode === 'subjects' && subjects.length === 0 ? (
            <div className="empty-state">No memory subjects indexed yet.</div>
          ) : mode === 'seai' ? (
            rawInputs.map((raw) => (
              <RawNode key={raw.id} raw={raw} selected={selected} setSelected={select} />
            ))
          ) : (
            subjects.map((subject) => (
              <SubjectNode key={subject.id} subject={subject} selected={selected} setSelected={select} />
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

const SubjectLinkList = ({ links }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
    {links.map((link) => (
      <div key={link.id} className="span-card">
        <div className="detail-meta">
          <Pill tone="green">{link.relation}</Pill>
          <Pill>{Math.round(link.confidence * 100)}%</Pill>
          {(link.event_time || link.time_label) && <Pill>{link.event_time || link.time_label}</Pill>}
        </div>
        <div className="evidence-text" style={{ color: 'var(--text-primary)' }}>
          {link.atom_content || link.episode_summary || link.reason}
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
        <div>{value}</div>
      </React.Fragment>
    ))}
  </div>
);
