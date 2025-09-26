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
  // New client-side options
  const [preferPresigned, setPreferPresigned] = useState(true);

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

        <div style={{ marginBottom: 12 }}>
          <label style={{ marginRight: 16 }}>
            <input
              type="checkbox"
              checked={preferPresigned}
              onChange={(e) => setPreferPresigned(e.target.checked)}
            />{" "}
            Prefer presigned URLs for media (if available)
          </label>
        </div>

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

          {/* New: Media and references extracted from the page */}
          {Array.isArray(result.images) && result.images.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Images</h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {result.images.map((img, idx) => (
                  <div
                    key={img.src || idx}
                    style={{ width: 160, textAlign: "center" }}
                  >
                    {/* prefer presigned URL from uploaded_media when available (toggle) */}
                    <img
                      src={
                        preferPresigned
                          ? (result.uploaded_media &&
                              result.uploaded_media.find(
                                (m) => m.source_url === img.src,
                              )?.presigned_url) ||
                            img.src
                          : img.src
                      }
                      alt={img.alt || img.title || ""}
                      style={{
                        maxWidth: "100%",
                        maxHeight: 120,
                        objectFit: "contain",
                        border: "1px solid #eee",
                        borderRadius: 4,
                      }}
                    />
                    <div style={{ fontSize: 11, color: "#555", marginTop: 4 }}>
                      {img.title || img.alt || img.src}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Array.isArray(result.videos) && result.videos.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Videos</h4>
              <div
                style={{ display: "flex", flexDirection: "column", gap: 12 }}
              >
                {result.videos.map((video, idx) => (
                  <div key={video.poster || idx}>
                    {Array.isArray(video.sources) &&
                    video.sources.length > 0 ? (
                      <video
                        controls
                        width="420"
                        poster={video.poster}
                        style={{ maxWidth: "100%", borderRadius: 4 }}
                      >
                        {video.sources.map((s, sidx) => {
                          // prefer presigned URL from uploaded_media matching source
                          const presigned =
                            result.uploaded_media &&
                            result.uploaded_media.find(
                              (m) => m.source_url === s.src,
                            )?.presigned_url;
                          return (
                            <source
                              key={s.src || sidx}
                              src={presigned || s.src}
                              type={s.type || ""}
                            />
                          );
                        })}
                        Your browser does not support the video tag.{" "}
                        <a
                          href={
                            (result.uploaded_media &&
                              result.uploaded_media.find(
                                (m) => m.source_url === video.sources[0].src,
                              )?.presigned_url) ||
                            video.sources[0].src
                          }
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Open video
                        </a>
                      </video>
                    ) : (
                      <div>
                        <a
                          href={
                            video.sources && video.sources[0]
                              ? video.sources[0].src
                              : "#"
                          }
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Open video
                        </a>
                      </div>
                    )}
                    <div style={{ fontSize: 12, color: "#555", marginTop: 6 }}>
                      {video.poster && (
                        <span>
                          Poster:{" "}
                          <a
                            href={video.poster}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {video.poster}
                          </a>
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Array.isArray(result.references) && result.references.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>References / Links</h4>
              <ul>
                {result.references.map((ref, idx) => (
                  <li
                    key={ref.href || idx}
                    style={{ fontSize: 13, marginBottom: 6 }}
                  >
                    <a
                      href={ref.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: "#007bff" }}
                    >
                      {ref.text || ref.title || ref.href}
                    </a>
                    {ref.title && (
                      <span
                        style={{ marginLeft: 8, color: "#666", fontSize: 12 }}
                      >
                        ({ref.title})
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {Array.isArray(result.embedded) && result.embedded.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Embedded</h4>
              <div
                style={{ display: "flex", flexDirection: "column", gap: 12 }}
              >
                {result.embedded.map((emb, idx) => (
                  <div key={emb.src || idx}>
                    <div
                      style={{ fontSize: 12, color: "#333", marginBottom: 6 }}
                    >
                      {emb.title || emb.type || emb.src}
                    </div>
                    <div
                      style={{
                        border: "1px solid #eee",
                        borderRadius: 4,
                        overflow: "hidden",
                      }}
                    >
                      <iframe
                        src={emb.src}
                        title={emb.title || `embedded-${idx}`}
                        width={emb.width || "560"}
                        height={emb.height || "315"}
                        style={{ width: "100%", height: 315, border: 0 }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Uploaded media section (presigned URLs) */}
          {Array.isArray(result.uploaded_media) &&
            result.uploaded_media.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <h4>Uploaded media (presigned URLs)</h4>
                <ul>
                  {result.uploaded_media.map((m, idx) => (
                    <li
                      key={m.s3_key || idx}
                      style={{ fontSize: 13, marginBottom: 6 }}
                    >
                      <div>
                        <strong>source:</strong>{" "}
                        <a
                          href={m.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {m.source_url}
                        </a>
                      </div>
                      <div>
                        <strong>s3_key:</strong> {m.s3_key || "-"}
                      </div>
                      <div>
                        <a
                          href={m.presigned_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Open presigned URL
                        </a>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

          {/* Debug: show raw media_refs if present */}
          {result.media_refs && (
            <div style={{ marginTop: 12 }}>
              <h4>Media references (raw)</h4>
              <pre style={{ fontSize: 12, background: "#f6f8fa", padding: 8 }}>
                {JSON.stringify(result.media_refs, null, 2)}
              </pre>
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
