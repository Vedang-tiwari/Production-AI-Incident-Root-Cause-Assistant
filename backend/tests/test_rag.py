import pytest
from backend.app.rag.embeddings import EmbeddingGenerator
from backend.app.rag.vector_store import InMemoryVectorStore


def test_embedding_generator():
    gen = EmbeddingGenerator(dimension=64)
    v1 = gen.generate_embedding("database connection pool timeout")
    v2 = gen.generate_embedding("database connection pool exhausted")
    v3 = gen.generate_embedding("frontend css styling header button")

    sim_related = gen.cosine_similarity(v1, v2)
    sim_unrelated = gen.cosine_similarity(v1, v3)

    assert sim_related > 0.5
    assert sim_related > sim_unrelated


def test_vector_store_search():
    store = InMemoryVectorStore()
    store.add_document(
        collection="runbooks",
        doc_id="RB-1",
        content="Database connection pool timeout troubleshooting. Check HikariPool and connection leak.",
        metadata={"service": "payment-service", "category": "database"},
    )
    store.add_document(
        collection="runbooks",
        doc_id="RB-2",
        content="Frontend webpack bundling and asset optimization.",
        metadata={"service": "frontend", "category": "build"},
    )

    results = store.search(
        collection="runbooks",
        query="database pool timeout",
        service="payment-service",
        top_k=1,
    )
    assert len(results) == 1
    assert results[0].id == "RB-1"

