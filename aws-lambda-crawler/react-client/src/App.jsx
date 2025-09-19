import React, { useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'REPLACE_WITH_API_URL';

export default function App() {
  const [url, setUrl] = useState(
    'https://wizeline.atlassian.net/wiki/spaces/VS/pages/4589223950/Technical+Overview',
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`HTTP ${res.status}: ${t}`);
      }
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 20, fontFamily: 'sans-serif' }}>
      <h2>Lambda Crawler Test</h2>
      <form onSubmit={handleSubmit} style={{ marginBottom: 12 }}>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com"
          style={{ width: 400, marginRight: 8 }}
        />
        <button type="submit" disabled={loading || !url}>
          {loading ? 'Crawling…' : 'Crawl'}
        </button>
      </form>

      {error && <div style={{ color: 'red' }}>Error: {error}</div>}

      {result && (
        <div>
          <h3>Result</h3>
          <div>
            <strong>URL:</strong> {result.url}
          </div>
          <div>
            <strong>Title:</strong> {result.title}
          </div>
          <div>
            <strong>Snippet:</strong> {result.text_snippet}
          </div>
        </div>
      )}

      <div style={{ marginTop: 18, fontSize: 12, color: '#666' }}>
        <div>
          API: <code>{API_URL}</code>
        </div>
        <div>Set `VITE_API_URL` in `.env` or environment when running.</div>
      </div>
    </div>
  );
}
