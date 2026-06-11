import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../components/AuthContext'

const STATUS_OPTIONS = ['new', 'reviewed', 'hired', 'rejected', 'archived']
const STATUS_CLS = { new:'status-new', reviewed:'status-reviewed', hired:'status-hired', rejected:'status-rejected', archived:'status-archived' }
const CATEGORIES = ['Technical', 'Communication', 'Problem Solving', 'Culture Fit', 'Leadership']
const SCORE_CATS = CATEGORIES

const CAT_ICONS = {
  Technical: '⌬', Communication: '◈', 'Problem Solving': '◉',
  'Culture Fit': '⬡', Leadership: '△', default: '◎'
}
const CAT_COLORS = {
  Technical: '#38bdf8', Communication: '#a78bfa', 'Problem Solving': '#f5a623',
  'Culture Fit': '#63d2b4', Leadership: '#ff6b7a'
}

function ScoreBar({ score }) {
  const pct = (score / 5) * 100
  const color = score >= 4 ? '#63d2b4' : score >= 3 ? '#f5a623' : '#ff6b7a'
  return (
    <div className="score-bar-wrap">
      <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

function Stars({ value, size = 14 }) {
  return (
    <div className="score-stars">
      {[1,2,3,4,5].map(n => (
        <span key={n} className={`score-star ${n <= value ? 'lit' : 'dim'}`} style={{fontSize:size}}>★</span>
      ))}
    </div>
  )
}

export default function CandidateDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [candidate, setCandidate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Score
  const [scoreForm, setScoreForm] = useState({ category: SCORE_CATS[0], score: 3, note: '' })
  const [scoreLoading, setScoreLoading] = useState(false)
  const [scoreMsg, setScoreMsg] = useState({ type: '', text: '' })

  // AI
  const [aiTab, setAiTab] = useState('Technical')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')
  const [aiSummaries, setAiSummaries] = useState({})

  // Admin notes
  const [editingNotes, setEditingNotes] = useState(false)
  const [notesVal, setNotesVal] = useState('')
  const [notesLoading, setNotesLoading] = useState(false)

  // Status
  const [statusLoading, setStatusLoading] = useState(false)

  async function load() {
    setLoading(true); setError('')
    try {
      const data = await api.getCandidate(id)
      setCandidate(data)
      setNotesVal(data.internal_notes || '')
      // Also load existing summaries
      const sumResp = await api.getAllSummaries(id)
      setAiSummaries(sumResp.summaries || {})
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [id])

  async function handleScore(e) {
    e.preventDefault(); setScoreMsg({ type:'', text:'' }); setScoreLoading(true)
    try {
      await api.submitScore(id, { category: scoreForm.category, score: parseInt(scoreForm.score), note: scoreForm.note || undefined })
      setScoreMsg({ type:'success', text:'Score recorded ✓' })
      setScoreForm({ category: SCORE_CATS[0], score: 3, note: '' })
      await load()
      setTimeout(() => setScoreMsg({ type:'', text:'' }), 3000)
    } catch (err) { setScoreMsg({ type:'error', text: err.message }) }
    finally { setScoreLoading(false) }
  }

  async function handleGenerate() {
    setAiLoading(true); setAiError('')
    try {
      const resp = await api.triggerSummary(id, aiTab)
      setAiSummaries(prev => ({ ...prev, [aiTab]: resp.summary }))
    } catch (err) { setAiError(err.message) }
    finally { setAiLoading(false) }
  }

  async function handleSaveNotes() {
    setNotesLoading(true)
    try {
      await api.updateCandidate(id, { internal_notes: notesVal })
      setCandidate(c => ({ ...c, internal_notes: notesVal }))
      setEditingNotes(false)
    } catch (err) { alert(err.message) }
    finally { setNotesLoading(false) }
  }

  async function handleStatusChange(s) {
    setStatusLoading(true)
    try {
      await api.updateCandidate(id, { status: s })
      setCandidate(c => ({ ...c, status: s }))
    } catch (err) { alert(err.message) }
    finally { setStatusLoading(false) }
  }

  async function handleDelete() {
    if (!window.confirm(`Archive ${candidate.name}? This is a soft delete.`)) return
    try { await api.deleteCandidate(id); navigate('/') }
    catch (err) { alert(err.message) }
  }

  if (loading) return (
    <div className="page">
      <header className="topbar">
        <div className="topbar-left">
          <div className="brand-mark"><div className="brand-icon">T</div><div className="brand-wordmark">Tech<span>Kraft</span></div></div>
        </div>
      </header>
      <div className="content"><div className="loading-state"><div className="loading-ring"/><span>Loading candidate profile…</span></div></div>
    </div>
  )
  if (error) return (
    <div className="page">
      <div className="content"><div className="alert alert-error"><span>⚠</span> {error}</div></div>
    </div>
  )
  if (!candidate) return null

  const avgScore = candidate.scores.length
    ? (candidate.scores.reduce((s,x) => s + x.score, 0) / candidate.scores.length).toFixed(1)
    : null

  const currentSummary = aiSummaries[aiTab]

  return (
    <div className="page">
      {/* Topbar */}
      <header className="topbar">
        <div className="topbar-left">
          <button className="btn btn-ghost" style={{fontSize:12}} onClick={() => navigate('/')}>← Back</button>
          <span className="topbar-sep">/</span>
          <div className="brand-mark" style={{cursor:'default'}}>
            <div className="brand-icon">T</div>
            <div className="brand-wordmark">Tech<span>Kraft</span></div>
          </div>
          <span className="topbar-sep">/</span>
          <span className="topbar-context">{candidate.name}</span>
        </div>
        <div className="topbar-right">
          <span className="role-badge" data-role={user?.role}>{user?.role}</span>
          <span className="topbar-mono">{user?.email}</span>
        </div>
      </header>

      <main className="content" style={{maxWidth:1200}}>
        {/* Hero Banner */}
        <div className="candidate-hero">
          <div className="candidate-hero-inner">
            <div className="candidate-avatar">
              <div className="candidate-avatar-inner">{candidate.name.charAt(0)}</div>
            </div>
            <div className="candidate-info">
              <h1 className="candidate-name">{candidate.name}</h1>
              <div className="candidate-email">{candidate.email}</div>
              <div className="candidate-role">{candidate.role_applied}</div>
              <div className="candidate-skills">
                {candidate.skills.map(s => <span key={s} className="skill-chip">{s}</span>)}
              </div>
            </div>
            <div className="candidate-meta">
              {avgScore && (
                <div className="score-orb">
                  <div className="score-orb-value">{avgScore}</div>
                  <div className="score-orb-label">avg / 5</div>
                </div>
              )}
              <div>
                {user?.role === 'admin' ? (
                  <select
                    className={`status-select ${STATUS_CLS[candidate.status]||''}`}
                    value={candidate.status}
                    onChange={e => handleStatusChange(e.target.value)}
                    disabled={statusLoading}
                  >
                    {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                ) : (
                  <span className={`status-pill ${STATUS_CLS[candidate.status]||''}`}>{candidate.status}</span>
                )}
              </div>
              <div className="candidate-date">
                Added {new Date(candidate.created_at).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'})}
              </div>
              {user?.role === 'admin' && (
                <button className="btn btn-danger" onClick={handleDelete}>Archive</button>
              )}
            </div>
          </div>
        </div>

        {/* Two-column layout */}
        <div className="detail-layout">
          {/* Left column */}
          <div className="detail-col">

            {/* Scores card */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-title-icon" style={{background:'rgba(99,210,180,0.12)',color:'var(--neo)'}}>◈</div>
                  Evaluation Scores
                  {user?.role === 'reviewer' && <span className="card-hint">(your scores only)</span>}
                </div>
                {candidate.scores.length > 0 && (
                  <span className="card-count">{candidate.scores.length}</span>
                )}
              </div>
              <div className="card-body">
                {candidate.scores.length === 0 ? (
                  <div style={{textAlign:'center',padding:'24px 0',color:'var(--ink-ghost)',fontSize:13}}>
                    No scores yet — submit the first evaluation below.
                  </div>
                ) : (
                  <div className="scores-list">
                    {candidate.scores.map(s => (
                      <div key={s.id} className="score-card">
                        <div className="score-top">
                          <span className="score-category-name">{s.category}</span>
                          <ScoreBar score={s.score} />
                          <Stars value={s.score} size={12} />
                          <span className="score-numval">{s.score}</span>
                        </div>
                        {s.note && <div className="score-note">{s.note}</div>}
                        <div className="score-meta">
                          {user?.role === 'admin' && (
                            <><span>rev:{s.reviewer_id.slice(0,8)}</span><span className="score-meta-sep">·</span></>
                          )}
                          <span>{new Date(s.created_at).toLocaleString('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'})}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Submit Score card */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-title-icon" style={{background:'rgba(245,166,35,0.12)',color:'var(--amber)'}}>★</div>
                  Submit Evaluation
                </div>
              </div>
              <div className="card-body">
                <form onSubmit={handleScore} className="score-form">
                  {scoreMsg.text && (
                    <div className={`alert alert-${scoreMsg.type}`}>
                      {scoreMsg.type === 'error' ? '⚠ ' : '✓ '}{scoreMsg.text}
                    </div>
                  )}
                  <div className="score-form-row">
                    <div className="field">
                      <label className="field-label">Category</label>
                      <select value={scoreForm.category} onChange={e => setScoreForm(f => ({...f, category: e.target.value}))}>
                        {SCORE_CATS.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                    <div className="field">
                      <label className="field-label">Score</label>
                      <div className="star-picker">
                        {[1,2,3,4,5].map(n => (
                          <button key={n} type="button"
                            className={`star-pick-btn ${n <= scoreForm.score ? 'lit' : ''}`}
                            onClick={() => setScoreForm(f => ({...f, score: n}))}>★</button>
                        ))}
                        <span className="star-pick-val">{scoreForm.score}/5</span>
                      </div>
                    </div>
                  </div>
                  <div className="field">
                    <label className="field-label">Note <span className="field-hint">(optional)</span></label>
                    <textarea
                      value={scoreForm.note}
                      onChange={e => setScoreForm(f => ({...f, note: e.target.value}))}
                      placeholder="Observations, evidence, context…"
                      rows={3}
                    />
                  </div>
                  <button type="submit" className="btn btn-primary" disabled={scoreLoading}>
                    {scoreLoading ? 'Recording…' : 'Submit Evaluation →'}
                  </button>
                </form>
              </div>
            </div>
          </div>

          {/* Right column */}
          <div className="detail-col">

            {/* AI Intelligence card */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-title-icon" style={{background:'linear-gradient(135deg,rgba(99,210,180,0.2),rgba(167,139,250,0.15))',color:'var(--neo)'}}>◈</div>
                  AI Intelligence
                </div>
                <button className="btn btn-secondary" onClick={handleGenerate} disabled={aiLoading}
                  style={{fontSize:12}}>
                  {aiLoading ? '◌ Thinking…' : currentSummary ? '⟳ Regenerate' : '▶ Analyse'}
                </button>
              </div>
              <div className="card-body ai-panel">
                {/* Category tabs */}
                <div className="ai-category-tabs">
                  {CATEGORIES.map(cat => (
                    <button key={cat}
                      className={`ai-tab ${aiTab === cat ? 'active' : ''} ${aiSummaries[cat] ? 'has-content' : ''}`}
                      onClick={() => setAiTab(cat)}
                      style={aiTab === cat ? {borderColor: CAT_COLORS[cat], color: CAT_COLORS[cat], background:`${CAT_COLORS[cat]}18`} : {}}
                    >
                      <span>{CAT_ICONS[cat]}</span>
                      {cat}
                    </button>
                  ))}
                </div>

                {/* Output area */}
                <div className="ai-output">
                  {aiLoading ? (
                    <div className="ai-generating">
                      <div className="ai-skeleton w90" />
                      <div className="ai-skeleton w85" />
                      <div className="ai-skeleton w60" />
                      <div className="ai-skeleton w75" />
                      <div className="ai-gen-label">
                        <div className="ai-gen-dot" />
                        Generating {aiTab} analysis…
                      </div>
                    </div>
                  ) : aiError ? (
                    <div className="alert alert-error" style={{marginBottom:0}}>⚠ {aiError}</div>
                  ) : currentSummary ? (
                    <div>
                      <div className="ai-header-row">
                        <span className="ai-badge-chip">AI</span>
                        <span className="ai-category-label"
                          style={{color: CAT_COLORS[aiTab]}}>{aiTab} Analysis</span>
                      </div>
                      <p className="ai-text">{currentSummary}</p>
                    </div>
                  ) : (
                    <div className="ai-empty">
                      <div className="ai-empty-icon">{CAT_ICONS[aiTab]}</div>
                      <div className="ai-empty-text">
                        No {aiTab} analysis yet.<br />Click <strong>Analyse</strong> to generate.
                      </div>
                    </div>
                  )}
                </div>

                {/* Mini legend showing which categories have been generated */}
                {Object.keys(aiSummaries).length > 0 && (
                  <div style={{marginTop:12,display:'flex',gap:6,flexWrap:'wrap'}}>
                    {CATEGORIES.filter(c => aiSummaries[c]).map(c => (
                      <span key={c} style={{
                        fontSize:10, fontFamily:'var(--font-mono)', letterSpacing:'0.5px',
                        padding:'2px 8px', borderRadius:3,
                        background:`${CAT_COLORS[c]}18`, color: CAT_COLORS[c],
                        border:`1px solid ${CAT_COLORS[c]}30`
                      }}>{c} ✓</span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Admin Notes card */}
            {user?.role === 'admin' && (
              <div className="card card-admin">
                <div className="card-header">
                  <div className="card-title">
                    <div className="card-title-icon" style={{background:'var(--violet-dim)',color:'var(--violet)'}}>⬡</div>
                    Internal Notes
                    <span className="admin-lock-badge">Admin</span>
                  </div>
                  {!editingNotes && (
                    <button className="btn btn-ghost" style={{fontSize:12}} onClick={() => setEditingNotes(true)}>Edit</button>
                  )}
                </div>
                <div className="card-body">
                  {editingNotes ? (
                    <div>
                      <textarea
                        value={notesVal}
                        onChange={e => setNotesVal(e.target.value)}
                        rows={5}
                        placeholder="Internal observations, hiring committee notes, red flags…"
                        style={{marginBottom:0}}
                      />
                      <div className="notes-actions">
                        <button className="btn btn-ghost" style={{fontSize:12}}
                          onClick={() => { setEditingNotes(false); setNotesVal(candidate.internal_notes||'') }}>Cancel</button>
                        <button className="btn btn-primary" style={{fontSize:12}}
                          onClick={handleSaveNotes} disabled={notesLoading}>
                          {notesLoading ? 'Saving…' : 'Save →'}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      {candidate.internal_notes
                        ? <div className="notes-display">{candidate.internal_notes}</div>
                        : <div className="notes-empty">No internal notes — click Edit to add.</div>
                      }
                    </div>
                  )}
                </div>
              </div>
            )}

          </div>
        </div>
      </main>
    </div>
  )
}
