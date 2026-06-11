import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../components/AuthContext'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      {/* Left visual panel */}
      <div className="login-visual">
        <div className="login-visual-bg" />
        <div className="login-visual-grid" />
        <div className="login-visual-content">
          <div className="login-visual-orb" />
          <h1 className="login-visual-title">
            Candidate<br /><span>Intelligence</span><br />Platform
          </h1>
          <p className="login-visual-desc">
            AI-powered scoring, deep behavioral profiling, and structured
            evaluation workflows — built for how modern teams actually hire.
          </p>
          <div className="login-visual-chips">
            {['Role-Based Access', 'AI Summaries', 'Score Analytics', 'Soft Delete', 'SSE Streaming'].map(c => (
              <span key={c} className="login-chip">{c}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="login-form-panel">
        <div className="login-card">
          <div className="login-logo">
            <div className="login-logo-icon">T</div>
            <div className="login-logo-name">Tech<span>Kraft</span></div>
          </div>

          <h2 className="login-heading">Sign in</h2>
          <p className="login-sub">Access your recruitment workspace</p>

          <form onSubmit={handleSubmit} className="login-form">
            {error && (
              <div className="alert alert-error">
                <span>⚠</span> {error}
              </div>
            )}
            <div className="field">
              <label className="field-label">Email address</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@techkraft.com"
                required
                autoFocus
              />
            </div>
            <div className="field" style={{ marginBottom: 20 }}>
              <label className="field-label">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
            <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? (
                <><span className="loading-ring" style={{ width: 14, height: 14, borderWidth: 2 }} /> Authenticating…</>
              ) : 'Sign in →'}
            </button>
          </form>

          <hr className="login-divider" />
          <p className="demo-label">Quick access — demo accounts</p>
          <div className="demo-accounts">
            <button className="demo-btn" onClick={() => { setEmail('admin@techkraft.com'); setPassword('admin123') }}>
              <span className="role-badge" data-role="admin">Admin</span>
              <div>
                <div>admin@techkraft.com</div>
                <div className="demo-email">Full access · internal notes · all scores</div>
              </div>
            </button>
            <button className="demo-btn" onClick={() => { setEmail('reviewer@techkraft.com'); setPassword('review123') }}>
              <span className="role-badge" data-role="reviewer">Reviewer</span>
              <div>
                <div>reviewer@techkraft.com</div>
                <div className="demo-email">Score candidates · own scores only</div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
