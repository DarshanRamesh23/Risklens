"""
RAG retrieval: given a vendor document chunk, find the most relevant internal
policy chunks by cosine distance in pgvector (`<=>` operator).
"""
from app.config import settings
from app.db.postgres import PolicyChunk, VendorChunk, get_session
from app.services.ingestion import embed_chunks


def get_vendor_chunks(vendor_id: int) -> list[VendorChunk]:
    session = get_session()
    try:
        return (
            session.query(VendorChunk)
            .filter(VendorChunk.vendor_id == vendor_id)
            .all()
        )
    finally:
        session.close()


def retrieve_relevant_policy_chunks(query_text: str, top_k: int = None) -> list[PolicyChunk]:
    top_k = top_k or settings.retrieval_top_k
    [embedding] = embed_chunks([query_text])

    session = get_session()
    try:
        # pgvector cosine distance operator `<=>`; ascending distance = most similar first.
        results = (
            session.query(PolicyChunk)
            .order_by(PolicyChunk.embedding.cosine_distance(embedding))
            .limit(top_k)
            .all()
        )
        return results
    finally:
        session.close()
