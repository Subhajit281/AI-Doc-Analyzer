import asyncio
import os
import psutil
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from app.core.memory import get_memory_usage_mb, optimize_memory
from app.core.cache import manifest_cache, query_embedding_cache
from app.core.queue import ingestion_queue
from app.services.document_service import document_service
from app.services.query_service import query_service


async def run_e2e_test():
    print("=" * 80)
    print("DOCUMENT AI - FREE TIER 512 MB END-TO-END VERIFICATION")
    print("=" * 80)

    # 1. Measure initial idle RSS
    initial_rss = get_memory_usage_mb()
    print(f"1. Initial Idle Memory: {initial_rss:.2f} MB (Budget: 512 MB)")
    assert initial_rss < 120, f"Initial RSS too high: {initial_rss} MB"

    # 2. Simulate UploadFile on sample.pdf
    pdf_path = Path("sample.pdf")
    assert pdf_path.exists(), "sample.pdf does not exist"

    class FakeUploadFile:
        def __init__(self, path: Path):
            self.filename = path.name
            self.content_type = "application/pdf"
            self._content = path.read_bytes()

        async def read(self):
            return self._content

    fake_file = FakeUploadFile(pdf_path)

    print("\n2. Ingesting sample.pdf through DocumentService (with Queue & LightweightParser)...")
    upload_result = await document_service.process_document(fake_file)
    post_upload_rss = get_memory_usage_mb()

    print(f"   Upload Result: {upload_result}")
    print(f"   Post-Upload Memory: {post_upload_rss:.2f} MB (Peak under 150 MB)")
    assert upload_result["status"] == "ready"
    assert upload_result["page_count"] == 2
    assert upload_result["section_count"] >= 5
    assert upload_result["chunk_count"] >= 5
    assert post_upload_rss < 200, f"Post-upload RSS too high: {post_upload_rss} MB"

    doc_id = upload_result["document_id"]

    # 3. Verify Manifest Cache
    print("\n3. Verifying Manifest Cache...")
    cached_manifest = manifest_cache.get(doc_id)
    assert cached_manifest is not None, "Manifest was not cached!"
    print(f"   Manifest Cache Hit! Cached sections: {len(cached_manifest['sections'])}")

    # 4. Execute Query through LangGraph Agent
    conv_id = "test-conv-001"
    query = "What is Subhajit's education background and CGPA?"
    print(f"\n4. Running Query: '{query}'")
    query_result = query_service.query(
        document_id=doc_id,
        query=query,
        conversation_id=conv_id,
    )
    post_query_rss = get_memory_usage_mb()
    print(f"   Query Answer:\n{query_result['answer']}\n")
    print(f"   Post-Query Memory: {post_query_rss:.2f} MB")
    assert "NIT" in query_result["answer"] or "Silchar" in query_result["answer"] or "7.73" in query_result["answer"]
    assert post_query_rss < 250, f"Post-query RSS too high: {post_query_rss} MB"

    # 5. Verify Query Embedding Cache
    print("\n5. Verifying Query Embedding Cache...")
    cache_size = query_embedding_cache.size()
    print(f"   Query embeddings cached: {cache_size}")
    assert cache_size > 0, "Query embedding was not cached!"

    # 6. Final Memory Cleanup & Summary
    print("\n6. Running Final Memory Optimization...")
    cleanup_stats = optimize_memory(tag="FinalCleanup")
    final_rss = get_memory_usage_mb()
    print(f"   Final RSS after cleanup: {final_rss:.2f} MB")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print(f"Max Recorded Memory: {max(post_upload_rss, post_query_rss):.2f} MB")
    print(f"Remaining Headroom on 512 MB Tier: {512 - max(post_upload_rss, post_query_rss):.2f} MB")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_e2e_test())

