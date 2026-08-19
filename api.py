from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.rag import RAGPipeline

app = FastAPI(title="WebRAG Studio API")

_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


class IngestRequest(BaseModel):
    url: str
    reset: bool = True


class AskRequest(BaseModel):
    question: str


@app.post("/ingest")
def ingest(request: IngestRequest):
    try:
        result = get_pipeline().ingest(request.url, reset=request.reset)
        return {
            "scope_prefix": result.scope_prefix,
            "pages_crawled": result.pages_crawled,
            "chunks_created": result.chunks_created,
            "chunks_stored": result.chunks_stored,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/ask")
def ask(request: AskRequest):
    try:
        result = get_pipeline().ask(request.question)
        return {
            "answer": result.answer,
            "sources": result.sources,
            "chunks_used": result.chunks_used,
            "verification_note": result.verification_note,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
def health():
    pipeline = get_pipeline()
    return {
        "ollama_available": pipeline.llm.is_available(),
        "vectors_stored": pipeline.vector_store.count(),
    }