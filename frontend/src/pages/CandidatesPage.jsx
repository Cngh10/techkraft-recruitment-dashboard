import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../components/AuthContext'

const STATUS_OPTS = ['', 'new', 'reviewed', 'hired', 'rejected']
const STATUS_CLS = { new:'status-new', reviewed:'status-reviewed', hired:'status-hired', rejected:'status-rejected', archived:'status-archived' }

function StatCell({ value, label, cls }) {
  return (
    <div className={`stat-cell ${cls}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

export default function CandidatesPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [candidates, setCandidates] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState({ status: '', role_applied: '', skill: '', keyword: '' })
  const [offset, setOffset] = useState(0)
  const [stats, setStats] = useState({ new:0, reviewed:0, hired:0, rejected:0 })
  const limit = 12

  // Add modal
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({ name:'', email:'', role_applied:'', skills:'' })
  const [addError, setAddError] = useState('')
  const [addLoading, setAddLoading] = useState(false)

  const fetchCandidates = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const data = await api.getCandidates({ ...filters, offset, limit })
      setCandidates(data.items)
      setTotal(data.total)
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }, [filters, offset, limit])

  // Fetch stats (all statuses)
  const fetchStats = useCallback(async () => {
    try {
      const [n, rv, h, rj] = await Promise.all([
        api.getCandidates({ status: 'new', limit: 1 }),
        api.getCandidates({ status: 'reviewed', limit: 1 }),
        api.getCandidates({ status: 'hired', limit: 1 }),
        api.getCandidates({ status: 'rejected', limit: 1 }),
      ])
      setStats({ new: n.total, reviewed: rv.total, hired: h.total, rejected: rj.total })
    } catch {}
  }, [])

  useEffect(() => { fetchCandidates() }, [fetchCandidates])
  useEffect(() => { fetchStats() }, [fetchStats])

  function setFilter(key, val) { setFilters(f => ({ ...f, [key]: val })); setOffset(0) }

  async function handleAdd(e) {
    e.preventDefault(); setAddError(''); setAddLoading(true)
    try {
      await api.createCandidate({
        name: addForm.name, email: addForm.email, role_applied: addForm.role_applied,
        skills: addForm.skills.split(',').map(s=>s.trim()).filter(Boolean),
      })
      setShowAdd(false); setAddForm({ name:'', email:'', role_applied:'', skills:'' })
      fetchCandidates(); fetchStats()
    } catch (err) { setAddError(err.message) }
    finally { setAddLoading(false) }
  }

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div className="page">
      <div className="candidates-page-bg" />

      {/* Topbar */}
      <header className="topbar">
        <div className="topbar-left">
          <div className="brand-mark">
            <div className="brand-icon">T</div>
            <div className="brand-wordmark">Tech<span>Kraft</span></div>
          </div>
          <span className="topbar-sep">/</span>
          <span className="topbar-context">Intelligence Platform</span>
        </div>
        <div className="topbar-right">
          <span className="role-badge" data-role={user?.role}>{user?.role}</span>
          <span className="topbar-mono">{user?.email}</span>
          <button className="btn btn-ghost" style={{fontSize:12}} onClick={logout}>Sign out</button>
        </div>
      </header>

      <main className="content" style={{position:'relative', zIndex:1}}>
        {/* Page Header */}
        <div className="page-header">
          <div>
            <div className="page-eyebrow">Recruitment · Pipeline</div>
            <h1 className="page-title">Candidate Review</h1>
            <p className="page-subtitle">
              {total} candidate{total !== 1 ? 's' : ''} in pipeline · page {currentPage} of {Math.max(totalPages,1)}
            </p>
          </div>
          {user?.role === 'admin' && (
            <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
              + Add Candidate
            </button>
          )}
        </div>

        {/* Stats Bar */}
        <div className="stats-bar">
          <StatCell value={stats.new}      label="New"      cls="stat-new" />
          <StatCell value={stats.reviewed} label="Reviewed" cls="stat-reviewed" />
          <StatCell value={stats.hired}    label="Hired"    cls="stat-hired" />
          <StatCell value={stats.rejected} label="Rejected" cls="stat-rejected" />
        </div>

        {/* Filter Bar */}
        <div className="filter-bar">
          <span className="filter-label">Filter</span>
          <input className="filter-input" placeholder="Search name, email, role…"
            value={filters.keyword} onChange={e => setFilter('keyword', e.target.value)} />
          <select className="filter-select" value={filters.status}
            onChange={e => setFilter('status', e.target.value)}>
            {STATUS_OPTS.map(s => <option key={s} value={s}>{s || 'All statuses'}</option>)}
          </select>
          <input className="filter-input" placeholder="Role…"
            value={filters.role_applied} onChange={e => setFilter('role_applied', e.target.value)} />
          <input className="filter-input" placeholder="Skill (e.g. React)…"
            value={filters.skill} onChange={e => setFilter('skill', e.target.value)} />
          {(filters.keyword || filters.status || filters.role_applied || filters.skill) && (
            <button className="btn btn-ghost" style={{fontSize:12}} onClick={() => {
              setFilters({ status:'', role_applied:'', skill:'', keyword:'' }); setOffset(0)
            }}>✕ Clear</button>
          )}
        </div>

        {/* Error */}
        {error && <div className="alert alert-error"><span>⚠</span> {error}</div>}

        {/* Table */}
        <div className="table-container">
          <div className="table-head-row">
            <div className="table-th">Name</div>
            <div className="table-th">Email</div>
            <div className="table-th">Role Applied</div>
            <div className="table-th">Skills</div>
            <div className="table-th">Status</div>
            <div className="table-th">Added</div>
            <div className="table-th"></div>
          </div>

          {loading ? (
            <div className="loading-state">
              <div className="loading-ring" />
              <span>Loading candidates…</span>
            </div>
          ) : candidates.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">◎</div>
              <p>No candidates match these filters.</p>
              {user?.role === 'admin' && (
                <button className="btn btn-primary" onClick={() => setShowAdd(true)}>Add candidate</button>
              )}
            </div>
          ) : (
            candidates.map(c => (
              <div key={c.id} className="candidate-row" onClick={() => navigate(`/candidates/${c.id}`)}>
                <div className="row-name">{c.name}</div>
                <div className="row-email">{c.email}</div>
                <div className="row-role">{c.role_applied}</div>
                <div className="row-skills">
                  {c.skills.slice(0, 3).map(s => <span key={s} className="skill-chip">{s}</span>)}
                  {c.skills.length > 3 && <span className="skill-more">+{c.skills.length - 3}</span>}
                </div>
                <div><span className={`status-pill ${STATUS_CLS[c.status]||''}`}>{c.status}</span></div>
                <div className="row-date">{new Date(c.created_at).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'})}</div>
                <div className="row-arrow">›</div>
              </div>
            ))
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <button className="btn btn-ghost" disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - limit))}>← Prev</button>
            <div style={{display:'flex',gap:5}}>
              {Array.from({length: Math.min(totalPages,7)}).map((_,i) => (
                <div key={i} className={`page-dot ${i === currentPage-1 ? 'active' : ''}`} />
              ))}
            </div>
            <span className="pagination-info">{currentPage} / {totalPages}</span>
            <button className="btn btn-ghost" disabled={offset + limit >= total}
              onClick={() => setOffset(offset + limit)}>Next →</button>
          </div>
        )}
      </main>

      {/* Add Modal */}
      {showAdd && (
        <div className="modal-backdrop" onClick={() => setShowAdd(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">Add Candidate</div>
              <button className="modal-close" onClick={() => setShowAdd(false)}>✕</button>
            </div>
            <form onSubmit={handleAdd}>
              {addError && <div className="alert alert-error"><span>⚠</span> {addError}</div>}
              <div className="field">
                <label className="field-label">Full Name</label>
                <input value={addForm.name} onChange={e => setAddForm(f=>({...f,name:e.target.value}))} required />
              </div>
              <div className="field">
                <label className="field-label">Email Address</label>
                <input type="email" value={addForm.email} onChange={e => setAddForm(f=>({...f,email:e.target.value}))} required />
              </div>
              <div className="field">
                <label className="field-label">Role Applied</label>
                <input value={addForm.role_applied} onChange={e => setAddForm(f=>({...f,role_applied:e.target.value}))} required />
              </div>
              <div className="field">
                <label className="field-label">Skills <span className="field-hint">(comma-separated)</span></label>
                <input value={addForm.skills} onChange={e => setAddForm(f=>({...f,skills:e.target.value}))} placeholder="React, Python, Docker…" />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowAdd(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={addLoading}>
                  {addLoading ? 'Adding…' : 'Add Candidate →'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
