# CUNY RAG Assistant

This project combines a FastAPI backend with a Vite frontend to answer CUNY policy and student-services questions from the indexed data under `data/`.

## Layout

- `backend/serve.py` exposes the HTTP API.
- `frontend/` contains the React UI.
- `src/pipeline/` contains ingestion, retrieval, embedding, chunking, and generation code.

## Backend

Run the API from the repository root:

```bash
./.venv/bin/python backend/serve.py
```

The service listens on `http://127.0.0.1:8000` and exposes:

- `GET /api/health`
- `POST /api/ask`

## Frontend

Run the UI separately from `frontend/`:

```bash
cd frontend
npm install
npm run dev
```

By default the frontend runs on `http://localhost:5173` and is allowed by the backend CORS config.

## Notes

- The backend warms the retriever on startup so the first request is faster.
- The server expects the generated data and embeddings already present under `data/`.