import { useState } from "react";

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);

  const handleAsk = () => {
    // Temporary mock response (replace later with backend)
    setAnswer("Students can apply using the CUNY application and must submit transcripts and required documents.");

    setSources([
      {
        title: "How to Apply - Baruch College",
        college: "Baruch College",
        source: "https://enrollmentmanagement.baruch.cuny.edu/"
      },
      {
        title: "How to Apply - Brooklyn College",
        college: "Brooklyn College",
        source: "https://www.brooklyn.edu/"
      }
    ]);
  };

  return (
    <div style={{ maxWidth: "700px", margin: "auto", padding: "20px", fontFamily: "Arial" }}>
      <h1>CUNY RAG Assistant</h1>

      <div style={{ marginBottom: "20px" }}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a CUNY question..."
          style={{ width: "70%", padding: "8px", marginRight: "10px" }}
        />
        <button onClick={handleAsk}>Ask</button>
      </div>

      {answer && (
        <div>
          <h2>Answer</h2>
          <p>{answer}</p>
        </div>
      )}

      {sources.length > 0 && (
        <div>
          <h3>Sources</h3>
          {sources.map((s, i) => (
            <div key={i} style={{ marginBottom: "10px" }}>
              <strong>{s.title}</strong>
              <p>{s.college}</p>
              <a href={s.source} target="_blank" rel="noreferrer">
                View Source
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;