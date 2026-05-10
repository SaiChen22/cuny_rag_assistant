import { useState } from "react";

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [model, setModel] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAsk = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setError("");
    setAnswer("");
    setSources([]);
    setModel("");

    try {
      const response = await fetch("http://127.0.0.1:8000/api/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: question,
          n_results: 5,
          filters: null,
        }),
      });

      if (!response.ok) {
        throw new Error("Backend request failed");
      }

      const data = await response.json();

      setAnswer(data.answer || "");
      setSources(data.sources || []);
      setModel(data.model || "");
    } catch (err) {
      console.error(err);
      setError("Could not connect to the backend. Make sure FastAPI is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f4f6fb",
        padding: "40px 20px",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <div
        style={{
          maxWidth: "800px",
          margin: "0 auto",
          background: "white",
          padding: "30px",
          borderRadius: "16px",
          boxShadow: "0 10px 30px rgba(0,0,0,0.08)",
        }}
      >
        <h1 style={{ marginBottom: "8px", color: "#1f2937" }}>
          CUNY RAG Assistant
        </h1>

        <p style={{ color: "#6b7280", marginBottom: "24px" }}>
          Ask a question about CUNY admissions, colleges, programs, or student resources.
        </p>

        <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAsk();
            }}
            placeholder="Example: How do I apply to CUNY?"
            style={{
              flex: 1,
              padding: "12px",
              borderRadius: "10px",
              border: "1px solid #d1d5db",
              fontSize: "16px",
            }}
          />

          <button
            onClick={handleAsk}
            disabled={loading || !question.trim()}
            style={{
              padding: "12px 20px",
              borderRadius: "10px",
              border: "none",
              background: loading || !question.trim() ? "#9ca3af" : "#2563eb",
              color: "white",
              fontSize: "16px",
              cursor: loading || !question.trim() ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Searching..." : "Ask"}
          </button>
        </div>

        {error && (
          <div
            style={{
              background: "#fee2e2",
              color: "#991b1b",
              padding: "12px",
              borderRadius: "10px",
              marginBottom: "20px",
            }}
          >
            {error}
          </div>
        )}

        {answer && (
          <div
            style={{
              background: "#f9fafb",
              padding: "20px",
              borderRadius: "12px",
              border: "1px solid #e5e7eb",
              marginBottom: "24px",
            }}
          >
            <h2 style={{ marginTop: 0, color: "#111827" }}>Answer</h2>
            <p style={{ lineHeight: "1.6", color: "#374151" }}>{answer}</p>

            {model && (
              <p style={{ fontSize: "13px", color: "#6b7280" }}>
                Model: {model}
              </p>
            )}
          </div>
        )}

        {sources.length > 0 && (
          <div>
            <h3 style={{ color: "#111827" }}>Sources</h3>

            {sources.map((s, i) => (
              <div
                key={i}
                style={{
                  padding: "16px",
                  border: "1px solid #e5e7eb",
                  borderRadius: "12px",
                  marginBottom: "12px",
                  background: "#ffffff",
                }}
              >
                <strong style={{ color: "#1f2937" }}>
                  {s.index ? `[${s.index}] ` : ""}
                  {s.title || "Untitled Source"}
                </strong>

                {s.college && (
                  <p style={{ margin: "6px 0", color: "#4b5563" }}>
                    {s.college}
                  </p>
                )}

                {s.category && (
                  <p style={{ margin: "6px 0", color: "#6b7280" }}>
                    Category: {s.category}
                  </p>
                )}

                {s.source && (
                  <a
                    href={s.source}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "#2563eb", fontWeight: "bold" }}
                  >
                    View Source
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;