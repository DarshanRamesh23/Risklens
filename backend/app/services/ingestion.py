"""
Ingestion service.

Pipeline: raw file -> extract text -> chunk -> embed -> store
  - raw text + metadata -> MongoDB (raw_documents)
  - chunks + embeddings   -> Postgres (policy_chunks or vendor_chunks), via pgvector

Chunking is intentionally simple (character windows with overlap) rather than
a semantic chunker, which is a reasonable trade-off to call out explicitly:
good enough for policy/questionnaire text, a known limitation for e.g. tables
inside PDFs, which would need a layout-aware chunker in a real system.
"""
from functools import lru_cache

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.db.mongo import store_raw_document
from app.db.postgres import PolicyChunk, VendorChunk, get_session


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    # Cached so the (relatively slow) model load happens once per process.
    return SentenceTransformer(settings.embedding_model_name)


def extract_text(filename: str, raw_bytes: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(__import__("io").BytesIO(raw_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return raw_bytes.decode("utf-8", errors="ignore")


def chunk_text(text: str, size: int = None, overlap: int = None) -> list[str]:
    size = size or settings.chunk_size_chars
    overlap = overlap or settings.chunk_overlap_chars
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    model = get_embedder()
    return model.encode(chunks, normalize_embeddings=True).tolist()


def ingest_policy_document(policy_name: str, filename: str, raw_bytes: bytes) -> dict:
    raw_text = extract_text(filename, raw_bytes)
    mongo_id = store_raw_document(None, filename, "policy", raw_text, {"policy_name": policy_name})

    chunks = chunk_text(raw_text)
    embeddings = embed_chunks(chunks) if chunks else []

    session = get_session()
    try:
        rows = [
            PolicyChunk(
                policy_name=policy_name,
                section_label=f"{policy_name} — chunk {i+1}",
                text=chunk,
                embedding=emb,
                mongo_doc_id=mongo_id,
            )
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]
        session.add_all(rows)
        session.commit()
        return {"policy_name": policy_name, "chunks_stored": len(rows), "mongo_doc_id": mongo_id}
    finally:
        session.close()


def ingest_vendor_document(vendor_id: int, filename: str, raw_bytes: bytes) -> dict:
    raw_text = extract_text(filename, raw_bytes)
    mongo_id = store_raw_document(vendor_id, filename, "vendor_doc", raw_text, {"vendor_id": vendor_id})

    chunks = chunk_text(raw_text)
    embeddings = embed_chunks(chunks) if chunks else []

    session = get_session()
    try:
        rows = [
            VendorChunk(
                vendor_id=vendor_id,
                doc_name=filename,
                text=chunk,
                embedding=emb,
                mongo_doc_id=mongo_id,
            )
            for chunk, emb in zip(chunks, embeddings)
        ]
        session.add_all(rows)
        session.commit()
        return {"vendor_id": vendor_id, "filename": filename, "chunks_stored": len(rows), "mongo_doc_id": mongo_id}
    finally:
        session.close()
