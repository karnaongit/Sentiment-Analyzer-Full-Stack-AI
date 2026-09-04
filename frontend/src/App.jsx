import { useEffect, useState } from 'react'
import axios from 'axios'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const colors = { Positive: '#16a34a', Negative: '#dc2626', Neutral: '#64748b' }

function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  function submit(event) {
    event.preventDefault()
    if (username === 'admin' && password === 'admin123') return onLogin()
    setError('Use the demo credentials: admin / admin123')
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <span className="eyebrow">AI INSIGHTS</span>
        <h1>Sentiment Analyzer</h1>
        <p>Turn customer conversations into clear, useful signals.</p>
        <form onSubmit={submit}>
          <label>
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder="admin"
            />
          </label>
          <label>
            Password
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              type="password"
              placeholder="admin123"
            />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button type="submit">Sign in</button>
        </form>
        <small>
          Demo access: <strong>admin / admin123</strong>
        </small>
      </section>
    </main>
  )
}

function UploadPanel({ onResults, onOpenHistory }) {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function analyze() {
    if (!file) return setError('Choose a .txt conversation first.')
    setLoading(true)
    setError('')
    try {
      const body = new FormData()
      body.append('file', file)
      const { data } = await axios.post(`${API_URL}/analyze`, body)
      onResults(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not reach the API. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="upload-panel">
      <span className="eyebrow">NEW ANALYSIS</span>
      <h2>Upload a conversation</h2>
      <p>
        Upload a UTF-8 <code>.txt</code> customer conversation to run the LangGraph agentic pipeline and store results in PostgreSQL.
      </p>
      <label className="drop-zone">
        <input
          type="file"
          accept=".txt,text/plain"
          onChange={(e) => {
            setFile(e.target.files?.[0] || null)
            setError('')
          }}
        />
        <span className="upload-icon">↑</span>
        <strong>{file ? file.name : 'Choose a .txt transcript'}</strong>
        <small>{file ? `${(file.size / 1024).toFixed(1)} KB selected` : 'UTF-8 text files only'}</small>
      </label>
      {error && <p className="form-error">{error}</p>}
      <button onClick={analyze} disabled={loading}>
        {loading ? 'Running LangGraph Agent…' : 'Analyze sentiment'}
      </button>
      <div className="upload-footer">
        <button className="text-link" onClick={onOpenHistory}>
          View previous analyses stored in database →
        </button>
      </div>
    </section>
  )
}

function HistoryView({ onSelect, onNew }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        setLoading(true)
        const { data } = await axios.get(`${API_URL}/conversations`)
        setHistory(data)
      } catch (err) {
        setError('Could not load analysis history from PostgreSQL.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <main className="dashboard">
      <header>
        <div>
          <span className="eyebrow">POSTGRESQL STORAGE</span>
          <h1>Analysis History</h1>
        </div>
        <button className="primary" onClick={onNew}>
          + New Analysis
        </button>
      </header>

      {loading && <p className="status-message">Loading history from PostgreSQL…</p>}
      {error && <p className="form-error">{error}</p>}

      {!loading && history.length === 0 && (
        <article className="panel empty-state">
          <p>No stored conversations found in PostgreSQL yet.</p>
          <button onClick={onNew}>Analyze your first conversation</button>
        </article>
      )}

      {!loading && history.length > 0 && (
        <section className="panel table-panel">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Analysis Date</th>
                  <th>Overall Sentiment</th>
                  <th>Dominant Sentiment</th>
                  <th>Sentences</th>
                  <th>Avg Confidence</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.filename}</strong>
                    </td>
                    <td>{item.uploaded_at ? new Date(item.uploaded_at).toLocaleString() : 'N/A'}</td>
                    <td>
                      <span className={`badge ${item.overall_sentiment}`}>{item.overall_sentiment}</span>
                    </td>
                    <td>{item.kpis?.dominant_sentiment || item.overall_sentiment}</td>
                    <td>{item.kpis?.total_sentences ?? '—'}</td>
                    <td>
                      {item.kpis?.average_confidence
                        ? `${(item.kpis.average_confidence * 100).toFixed(1)}%`
                        : '—'}
                    </td>
                    <td>
                      <button className="secondary sm-btn" onClick={() => onSelect(item.id)}>
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  )
}

function Dashboard({ analysis, onNew, onOpenHistory }) {
  const { kpis, sentences, overall_sentiment: overall, summary, insights, filename } = analysis
  const chartData = ['Positive', 'Negative', 'Neutral'].map((name) => ({
    name,
    value: kpis[name.toLowerCase()] || 0,
  }))
  const cards = [
    ['Total sentences', kpis.total_sentences, ''],
    ['Positive', kpis.positive, `${kpis.positive_percentage}%`],
    ['Negative', kpis.negative, `${kpis.negative_percentage}%`],
    ['Neutral', kpis.neutral, `${kpis.neutral_percentage}%`],
  ]

  return (
    <main className="dashboard">
      <header>
        <div>
          <span className="eyebrow">LANGGRAPH AGENT COMPLETE</span>
          <h1>Conversation insights</h1>
          {filename && <small className="file-tag">File: {filename}</small>}
        </div>
        <div className="btn-group">
          <button className="secondary" onClick={onOpenHistory}>
            History
          </button>
          <button className="secondary" onClick={onNew}>
            Analyze another
          </button>
        </div>
      </header>

      <section className="hero-card">
        <div>
          <span className="muted">Overall sentiment</span>
          <h2 className={`sentiment ${overall}`}>{overall}</h2>
          <p>Dominant sentiment classified across this conversation.</p>
        </div>
        <div className="confidence">
          <span>Average confidence</span>
          <strong>{(kpis.average_confidence * 100).toFixed(1)}%</strong>
        </div>
      </section>

      <section className="kpi-grid">
        {cards.map(([label, value, detail]) => (
          <article className="kpi-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{detail}</small>
          </article>
        ))}
      </section>

      <section className="content-grid">
        <article className="panel chart-panel">
          <div>
            <span className="eyebrow">BREAKDOWN</span>
            <h2>Sentiment mix</h2>
          </div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={210}>
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={58}
                  outerRadius={82}
                  paddingAngle={3}
                >
                  {chartData.map((entry) => (
                    <Cell key={entry.name} fill={colors[entry.name]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [`${value} sentences`, name]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="legend">
              {chartData.map((item) => (
                <span key={item.name}>
                  <i style={{ background: colors[item.name] }} />
                  {item.name} <b>{item.value}</b>
                </span>
              ))}
            </div>
          </div>
        </article>

        <article className="panel insights">
          <span className="eyebrow">CALL INSIGHTS</span>
          <h2>What the numbers say</h2>
          <dl>
            <div>
              <dt>Positive ratio</dt>
              <dd>{kpis.positive_percentage}%</dd>
            </div>
            <div>
              <dt>Negative ratio</dt>
              <dd>{kpis.negative_percentage}%</dd>
            </div>
            <div>
              <dt>Neutral ratio</dt>
              <dd>{kpis.neutral_percentage}%</dd>
            </div>
            <div>
              <dt>Dominant sentiment</dt>
              <dd>{kpis.dominant_sentiment}</dd>
            </div>
          </dl>
        </article>
      </section>

      {insights && (
        <section className="panel agentic-insights">
          <span className="eyebrow">LANGGRAPH AGENT INSIGHTS</span>
          <h2>{insights.analysis_type || 'Agent Analysis'}</h2>
          <p className="insight-tone">
            <strong>Overall tone:</strong> {insights.overall_tone}
          </p>
          <div className="insight-details">
            <div>
              <span className="muted">Risk evaluation:</span>
              <strong>{insights.churn_risk}</strong>
            </div>
            <div>
              <span className="muted">Action signal:</span>
              <strong>{insights.recommended_action}</strong>
            </div>
            <div>
              <span className="muted">Closing resolution:</span>
              <strong>{insights.resolution_signal}</strong>
            </div>
          </div>
        </section>
      )}

      <section className="panel summary">
        <span className="eyebrow">EXTRACTIVE SUMMARY</span>
        <h2>Conversation summary</h2>
        <p>{summary}</p>
      </section>

      <section className="panel table-panel">
        <div>
          <span className="eyebrow">SENTENCE-LEVEL ANALYSIS</span>
          <h2>Every moment, classified</h2>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Sentence</th>
                <th>Sentiment</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {sentences.map((row, index) => (
                <tr key={`${row.text}-${index}`}>
                  <td>{row.text}</td>
                  <td>
                    <span className={`badge ${row.sentiment}`}>{row.sentiment}</span>
                  </td>
                  <td>{(row.confidence * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(false)
  const [view, setView] = useState('upload') // 'upload' | 'history' | 'dashboard'
  const [analysis, setAnalysis] = useState(null)
  const [loadingItem, setLoadingItem] = useState(false)

  async function handleSelectHistoryItem(id) {
    try {
      setLoadingItem(true)
      const { data } = await axios.get(`${API_URL}/conversations/${id}`)
      setAnalysis(data)
      setView('dashboard')
    } catch (err) {
      alert('Failed to load conversation details from PostgreSQL.')
    } finally {
      setLoadingItem(false)
    }
  }

  function handleNewAnalysis() {
    setAnalysis(null)
    setView('upload')
  }

  if (!loggedIn) return <Login onLogin={() => setLoggedIn(true)} />

  return (
    <div className="app-shell">
      <nav>
        <span className="brand-mark">S</span>
        <strong>Sentiment Analyzer</strong>
        <div className="nav-links">
          <button
            className={`nav-btn ${view === 'upload' ? 'active' : ''}`}
            onClick={handleNewAnalysis}
          >
            New Analysis
          </button>
          <button
            className={`nav-btn ${view === 'history' ? 'active' : ''}`}
            onClick={() => setView('history')}
          >
            History
          </button>
        </div>
        <span className="nav-user">admin</span>
      </nav>

      {loadingItem && <p className="global-loader">Loading conversation from database…</p>}

      {!loadingItem && view === 'upload' && (
        <UploadPanel
          onResults={(data) => {
            setAnalysis(data)
            setView('dashboard')
          }}
          onOpenHistory={() => setView('history')}
        />
      )}

      {!loadingItem && view === 'history' && (
        <HistoryView
          onSelect={handleSelectHistoryItem}
          onNew={handleNewAnalysis}
        />
      )}

      {!loadingItem && view === 'dashboard' && analysis && (
        <Dashboard
          analysis={analysis}
          onNew={handleNewAnalysis}
          onOpenHistory={() => setView('history')}
        />
      )}
    </div>
  )
}
