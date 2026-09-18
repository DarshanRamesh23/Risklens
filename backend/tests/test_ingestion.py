from app.services.ingestion import chunk_text


def test_chunk_text_empty():
    assert chunk_text("") == []


def test_chunk_text_single_chunk_when_short():
    text = "short policy clause"
    chunks = chunk_text(text, size=1000, overlap=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_overlap():
    text = "a" * 500
    chunks = chunk_text(text, size=200, overlap=50)
    assert len(chunks) > 1
    # consecutive chunks should share the overlap region
    assert chunks[0][-50:] == chunks[1][:50]


def test_chunk_text_covers_full_text():
    text = "word " * 100
    chunks = chunk_text(text, size=100, overlap=20)
    rebuilt_length = sum(len(c) for c in chunks)
    assert rebuilt_length >= len(text.strip())
