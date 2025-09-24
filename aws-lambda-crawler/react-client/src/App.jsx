import React, { useState, useEffect } from "react";

const API_URL = import.meta.env.VITE_API_URL || "REPLACE_WITH_API_URL";

export default function App() {
  const [url, setUrl] = useState(
    "https://wizeline.atlassian.net/wiki/spaces/VS/pages/4589223950/Technical+Overview",
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [full, setFull] = useState(true);

  // New Bedrock-related states
  const [enableSummary, setEnableSummary] = useState(true);
  const [modelId, setModelId] = useState("");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokenCount, setMaxTokenCount] = useState(2048);
  const [checkingModels, setCheckingModels] = useState(false);
  const [availableModels, setAvailableModels] = useState([]);

  const availableModelOptions = [
    { value: "", label: "Default (amazon.titan-text-express-v1)" },
    {
      value: "amazon.titan-text-express-v1",
      label: "Amazon Titan Text Express v1",
    },
    { value: "amazon.titan-text-lite-v1", label: "Amazon Titan Text Lite v1" },
    {
      value: "anthropic.claude-3-haiku-20240307-v1:0",
      label: "Anthropic Claude 3 Haiku",
    },
    {
      value: "anthropic.claude-3-sonnet-20240229-v1:0",
      label: "Anthropic Claude 3 Sonnet",
    },
    {
      value: "anthropic.claude-3-5-sonnet-20240620-v1:0",
      label: "Anthropic Claude 3.5 Sonnet",
    },
  ];

  async function checkModelAccess() {
    setCheckingModels(true);
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "check_models" }),
      });
      if (res.ok) {
        const data = await res.json();
        setAvailableModels(data.accessible_models || []);
      }
    } catch (err) {
      console.error("Error checking model access:", err);
    } finally {
      setCheckingModels(false);
    }
  }

  // Check model access on component mount
  useEffect(() => {
    if (enableSummary) {
      checkModelAccess();
    }
  }, [enableSummary]);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const requestBody = { url, full };

      // Add Bedrock parameters if summary is enabled
      if (enableSummary) {
        if (modelId) {
          requestBody.model_id = modelId;
        }
        requestBody.text_config = {
          temperature: parseFloat(temperature),
          maxTokenCount: parseInt(maxTokenCount),
        };
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
        <div style={{ marginBottom: 12 }}>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            style={{ width: "100%", marginBottom: 8, padding: 8 }}
          />
        </div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ marginRight: 16 }}>
            <input
              type="checkbox"
              checked={full}
              onChange={(e) => setFull(e.target.checked)}
            />{" "}
            Full content
          </label>

          <label>
            <input
              type="checkbox"
              checked={enableSummary}
              onChange={(e) => setEnableSummary(e.target.checked)}
            />{" "}
            Enable AI Summary (Bedrock)
          </label>
        </div>

        {enableSummary && (
          <div
            style={{
              border: "1px solid #ddd",
              padding: 12,
              marginBottom: 12,
              backgroundColor: "#f9f9f9",
              borderRadius: 4,
            }}
          >
            <h4 style={{ margin: "0 0 12px 0", fontSize: 14 }}>
              Bedrock Configuration
              <button
                type="button"
                onClick={checkModelAccess}
                disabled={checkingModels}
                style={{
                  marginLeft: 8,
                  fontSize: 12,
                  padding: "2px 8px",
                  backgroundColor: "#007bff",
                  color: "white",
                  border: "none",
                  borderRadius: 3,
                  cursor: checkingModels ? "wait" : "pointer",
                }}
              >
                {checkingModels ? "Checking..." : "Check Model Access"}
              </button>
            </h4>

            {availableModels.length > 0 && (
              <div style={{ fontSize: 12, color: "green", marginBottom: 8 }}>
                ✓ Accessible models: {availableModels.join(", ")}
              </div>
            )}

            <div style={{ marginBottom: 8 }}>
              <label
                style={{ display: "block", fontSize: 12, marginBottom: 4 }}
              >
                Model:
              </label>
              <select
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
                style={{ width: "100%", padding: 4 }}
              >
                {availableModelOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                    {availableModels.includes(option.value) && option.value
                      ? " ✓"
                      : ""}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ flex: 1 }}>
                <label
                  style={{ display: "block", fontSize: 12, marginBottom: 4 }}
                >
                  Temperature: {temperature}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(e.target.value)}
                  style={{ width: "100%" }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label
                  style={{ display: "block", fontSize: 12, marginBottom: 4 }}
                >
                  Max Tokens: {maxTokenCount}
                </label>
                <input
                  type="range"
                  min="512"
                  max="8192"
                  step="256"
                  value={maxTokenCount}
                  onChange={(e) => setMaxTokenCount(e.target.value)}
                  style={{ width: "100%" }}
                />
              </div>
            </div>
          </div>
        )}

        <button type="submit" disabled={loading || !url}>
          {loading ? "Crawling…" : "Crawl"}
        </button>
      </form>

      {error && <div style={{ color: "red" }}>Error: {error}</div>}

      {result && (
        <div>
          <h3>Result</h3>
          <div style={{ marginBottom: 8 }}>
            <strong>URL:</strong> {result.url}
          </div>
          <div style={{ marginBottom: 8 }}>
            <strong>Title:</strong> {result.title}
          </div>

          {/* AI Summary Section */}
          {result.summary && (
            <div
              style={{
                border: "1px solid #28a745",
                backgroundColor: "#f8fff9",
                padding: 12,
                marginBottom: 12,
                borderRadius: 4,
              }}
            >
              <h4
                style={{ margin: "0 0 8px 0", color: "#28a745", fontSize: 16 }}
              >
                🤖 AI Summary
                {result.summary.model_used && (
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: "normal",
                      color: "#666",
                      marginLeft: 8,
                    }}
                  >
                    (via {result.summary.model_used})
                  </span>
                )}
              </h4>
              <div
                style={{
                  whiteSpace: "pre-wrap",
                  fontFamily: "Georgia, serif",
                  lineHeight: 1.5,
                  fontSize: 14,
                }}
              >
                {result.summary.result?.outputText ||
                  JSON.stringify(result.summary, null, 2)}
              </div>
            </div>
          )}

          {/* Summary Error Section */}
          {result.summary_error && (
            <div
              style={{
                border: "1px solid #dc3545",
                backgroundColor: "#fff8f8",
                padding: 12,
                marginBottom: 12,
                borderRadius: 4,
              }}
            >
              <h4
                style={{ margin: "0 0 8px 0", color: "#dc3545", fontSize: 16 }}
              >
                ⚠️ Summary Error
              </h4>
              <div style={{ fontSize: 12, marginBottom: 8, color: "#721c24" }}>
                <strong>Error:</strong> {result.summary_error.error}
              </div>

              {result.summary_error.help && (
                <div
                  style={{
                    fontSize: 12,
                    color: "#856404",
                    backgroundColor: "#fff3cd",
                    padding: 8,
                    borderRadius: 3,
                  }}
                >
                  <strong>Help:</strong> {result.summary_error.help.message}
                  {result.summary_error.help.instructions && (
                    <ol style={{ marginTop: 8, marginBottom: 0 }}>
                      {result.summary_error.help.instructions.map(
                        (instruction, idx) => (
                          <li key={idx}>{instruction}</li>
                        ),
                      )}
                    </ol>
                  )}
                  {result.summary_error.help.console_url && (
                    <div style={{ marginTop: 8 }}>
                      <a
                        href={result.summary_error.help.console_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: "#007bff" }}
                      >
                        → Open AWS Bedrock Console
                      </a>
                    </div>
                  )}
                </div>
              )}

              <details style={{ marginTop: 8, fontSize: 11 }}>
                <summary style={{ cursor: "pointer", color: "#6c757d" }}>
                  Show technical details
                </summary>
                <pre
                  style={{
                    fontSize: 10,
                    color: "#6c757d",
                    backgroundColor: "#f8f9fa",
                    padding: 8,
                    borderRadius: 3,
                    overflow: "auto",
                    marginTop: 4,
                  }}
                >
                  {result.summary_error.trace}
                </pre>
              </details>
            </div>
          )}

          <div style={{ marginBottom: 8 }}>
            <strong>Content Preview:</strong>
          </div>
          <div
            style={{
              maxHeight: 200,
              overflow: "auto",
              border: "1px solid #ddd",
              padding: 8,
              backgroundColor: "#f9f9f9",
              fontSize: 12,
              fontFamily: "monospace",
            }}
          >
            {result.text_snippet}
          </div>

          {typeof result.resource_count !== "undefined" && (
            <div style={{ marginTop: 8 }}>
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
      )}

      <div style={{ marginTop: 18, fontSize: 12, color: "#666" }}>
        <div>
          API: <code>{API_URL}</code>
        </div>
        <div>Set `VITE_API_URL` in `.env` or environment when running.</div>
        <div
          style={{
            marginTop: 8,
            padding: 8,
            backgroundColor: "#e7f3ff",
            borderRadius: 3,
          }}
        >
          <strong>New:</strong> AI-powered summarization using AWS Bedrock!
          Enable the checkbox above to get AI-generated summaries of crawled
          content.
        </div>
      </div>
    </div>
  );
}
