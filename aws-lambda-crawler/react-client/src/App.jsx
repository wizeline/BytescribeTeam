import React, { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "REPLACE_WITH_API_URL";

export default function App() {
  const [url, setUrl] = useState(
    "https://wizeline.atlassian.net/wiki/spaces/VS/pages/4589223950/Technical+Overview",
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [full, setFull] = useState(true);
  const [action, setAction] = useState("parse"); // "parse", "index", or "summarize"

  // Summarization options
  const [summaryLength, setSummaryLength] = useState("medium");
  const [focus, setFocus] = useState("");
  const [modelId, setModelId] = useState(
    "anthropic.claude-3-haiku-20240307-v1:0",
  );

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const requestBody = { url, full };

      if (action === "index") {
        requestBody.action = "index";
      } else if (action === "summarize") {
        requestBody.action = "summarize";
        requestBody.summary_length = summaryLength;
        requestBody.model_id = modelId;
        if (focus.trim()) {
          requestBody.focus = focus.trim();
        }
      }

      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
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
    <div style={{ padding: 20, fontFamily: "sans-serif" }}>
      <h2>Lambda Crawler Test</h2>
      <form onSubmit={handleSubmit} style={{ marginBottom: 12 }}>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com"
          style={{ width: 400, marginRight: 8 }}
        />
        <label style={{ marginRight: 8, marginLeft: 8 }}>
          <input
            type="checkbox"
            checked={full}
            onChange={(e) => setFull(e.target.checked)}
          />{" "}
          Full content
        </label>
        <label style={{ marginRight: 8, marginLeft: 8 }}>
          <select
            value={action}
            onChange={(e) => setAction(e.target.value)}
            style={{ marginRight: 8 }}
          >
            <option value="parse">Parse HTML</option>
            <option value="index">Create Document (Index)</option>
            <option value="summarize">Summarize Content</option>
          </select>
        </label>

        {/* Summarization options - show only when summarize action is selected */}
        {action === "summarize" && (
          <div style={{ marginTop: 10, marginBottom: 10 }}>
            <div style={{ marginBottom: 8 }}>
              <label style={{ marginRight: 8 }}>
                Summary Length:
                <select
                  value={summaryLength}
                  onChange={(e) => setSummaryLength(e.target.value)}
                  style={{ marginLeft: 8, marginRight: 16 }}
                >
                  <option value="short">Short (1-2 sentences)</option>
                  <option value="medium">Medium (1 paragraph)</option>
                  <option value="long">Long (2-3 paragraphs)</option>
                </select>
              </label>
            </div>

            <div style={{ marginBottom: 8 }}>
              <label style={{ marginRight: 8 }}>
                Focus Area (optional):
                <input
                  type="text"
                  value={focus}
                  onChange={(e) => setFocus(e.target.value)}
                  placeholder="e.g., technical details, key findings, action items"
                  style={{ marginLeft: 8, width: 300 }}
                />
              </label>
            </div>

            <div style={{ marginBottom: 8 }}>
              <label style={{ marginRight: 8 }}>
                Model:
                <select
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  style={{ marginLeft: 8, width: 350 }}
                >
                  <option value="anthropic.claude-3-haiku-20240307-v1:0">
                    Claude 3 Haiku (Fast & Cost-effective)
                  </option>
                  <option value="anthropic.claude-3-sonnet-20240229-v1:0">
                    Claude 3 Sonnet (Balanced)
                  </option>
                  <option value="anthropic.claude-3-opus-20240229-v1:0">
                    Claude 3 Opus (Highest Quality)
                  </option>
                  <option value="amazon.titan-text-express-v1">
                    Amazon Titan Express
                  </option>
                  <option value="amazon.titan-text-lite-v1">
                    Amazon Titan Lite
                  </option>
                  <option value="ai21.j2-mid-v1">AI21 J2 Mid</option>
                  <option value="ai21.j2-ultra-v1">AI21 J2 Ultra</option>
                </select>
              </label>
            </div>
          </div>
        )}

        <button type="submit" disabled={loading || !url}>
          {loading
            ? "Processing…"
            : action === "index"
            ? "Index"
            : action === "summarize"
            ? "Summarize"
            : "Crawl"}
        </button>
      </form>

      {error && <div style={{ color: "red" }}>Error: {error}</div>}

      {result && (
        <div>
          <h3>Result</h3>
          <div>
            <strong>URL:</strong> {result.url}
          </div>

          {/* Show summary results if action was "summarize" */}
          {action === "summarize" && result.document?.summary && (
            <div style={{ marginTop: 15 }}>
              <h4>Summary</h4>
              <div
                style={{
                  background: "#f8f9ff",
                  padding: 15,
                  marginTop: 8,
                  borderLeft: "4px solid #007acc",
                  borderRadius: "4px",
                }}
              >
                {result.document.summary}
              </div>

              {/* Summary metadata */}
              {result.document.summary_metadata && (
                <div style={{ marginTop: 10, fontSize: 12, color: "#666" }}>
                  <div>
                    <strong>Model:</strong>{" "}
                    {result.document.summary_metadata.model_used}
                  </div>
                  <div>
                    <strong>Input length:</strong>{" "}
                    {result.document.summary_metadata.input_length} characters
                  </div>
                  <div>
                    <strong>Summary length:</strong>{" "}
                    {result.document.summary_metadata.summary_length} characters
                  </div>
                  {result.document.summary_metadata.focus && (
                    <div>
                      <strong>Focus:</strong>{" "}
                      {result.document.summary_metadata.focus}
                    </div>
                  )}
                  {result.document.summary_metadata.length_setting && (
                    <div>
                      <strong>Length setting:</strong>{" "}
                      {result.document.summary_metadata.length_setting}
                    </div>
                  )}
                  {result.document.summary_metadata.error && (
                    <div style={{ color: "red" }}>
                      <strong>Error:</strong>{" "}
                      {result.document.summary_metadata.error}
                    </div>
                  )}
                </div>
              )}

              {/* Original document info */}
              <div
                style={{
                  marginTop: 15,
                  paddingTop: 15,
                  borderTop: "1px solid #eee",
                }}
              >
                <h5>Original Document</h5>
                <div>
                  <strong>Title:</strong> {result.document.title}
                </div>
                <div>
                  <strong>Content Length:</strong>{" "}
                  {result.document.text?.length ||
                    result.document.content?.length ||
                    0}{" "}
                  characters
                </div>
              </div>
            </div>
          )}

          {/* Show document structure if action was "index" */}
          {result.document && action !== "summarize" ? (
            <div>
              <div>
                <strong>Title:</strong> {result.document.title}
              </div>
              <div>
                <strong>Content Length:</strong>{" "}
                {result.document.content?.length || 0} characters
              </div>
              <div>
                <strong>Chunks:</strong> {result.document.chunks?.length || 0}
              </div>
              {result.document.chunks && result.document.chunks.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <strong>First chunk preview:</strong>
                  <div
                    style={{
                      background: "#f5f5f5",
                      padding: 10,
                      marginTop: 5,
                      fontSize: 12,
                      maxHeight: 200,
                      overflow: "auto",
                    }}
                  >
                    {result.document.chunks[0].text.substring(0, 500)}
                    {result.document.chunks[0].text.length > 500 && "..."}
                  </div>
                </div>
              )}
              {typeof result.resource_count !== "undefined" && (
                <div>
                  <strong>Resources downloaded:</strong> {result.resource_count}
                </div>
              )}
              {Array.isArray(result.failed_resources) &&
                result.failed_resources.length > 0 && (
                  <div>
                    <strong>Failed resources:</strong>
                    <ul>
                      {result.failed_resources.map((r) => (
                        <li key={r} style={{ fontSize: 12 }}>
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>
          ) : action !== "summarize" ? (
            <div>
              <div>
                <strong>Title:</strong> {result.title}
              </div>
              <div>
                <strong>Snippet:</strong> {result.text_snippet}
              </div>
              {typeof result.resource_count !== "undefined" && (
                <div>
                  <strong>Resources downloaded:</strong> {result.resource_count}
                </div>
              )}
              {Array.isArray(result.failed_resources) &&
                result.failed_resources.length > 0 && (
                  <div>
                    <strong>Failed resources:</strong>
                    <ul>
                      {result.failed_resources.map((r) => (
                        <li key={r} style={{ fontSize: 12 }}>
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>
          ) : (
            // Fallback for summarize action when no document structure is returned
            <div style={{ marginTop: 15 }}>
              {result.summary ? (
                <div>
                  <h4>Summary</h4>
                  <div
                    style={{
                      background: "#f8f9ff",
                      padding: 15,
                      marginTop: 8,
                      borderLeft: "4px solid #007acc",
                      borderRadius: "4px",
                    }}
                  >
                    {result.summary}
                  </div>

                  {/* Summary metadata from root level */}
                  {(result.model_used ||
                    result.input_length ||
                    result.summary_length) && (
                    <div style={{ marginTop: 10, fontSize: 12, color: "#666" }}>
                      {result.model_used && (
                        <div>
                          <strong>Model:</strong> {result.model_used}
                        </div>
                      )}
                      {result.input_length && (
                        <div>
                          <strong>Input length:</strong> {result.input_length}{" "}
                          characters
                        </div>
                      )}
                      {result.summary_length && (
                        <div>
                          <strong>Summary length:</strong>{" "}
                          {result.summary_length} characters
                        </div>
                      )}
                      {result.focus && (
                        <div>
                          <strong>Focus:</strong> {result.focus}
                        </div>
                      )}
                      {result.length_setting && (
                        <div>
                          <strong>Length setting:</strong>{" "}
                          {result.length_setting}
                        </div>
                      )}
                      {result.error && (
                        <div style={{ color: "red" }}>
                          <strong>Error:</strong> {result.error}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <strong>No summary available</strong>
                  {result.error && (
                    <div style={{ color: "red", marginTop: 8 }}>
                      Error: {result.error}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div style={{ marginTop: 18, fontSize: 12, color: "#666" }}>
        <div>
          API: <code>{API_URL}</code>
        </div>
        <div>Set `VITE_API_URL` in `.env` or environment when running.</div>
      </div>
    </div>
  );
}
