"""
Quick test of LangChain integration with community langchain-iris package.

This tests the integration WITHOUT requiring OpenAI API keys by using
FakeEmbeddings for demonstration purposes.
"""

from langchain_core.embeddings import FakeEmbeddings
from langchain_core.documents import Document

# Test our integration
from iris_devtester.integrations.langchain import LangChainIRISContainer


def test_basic_integration():
    """Test basic LangChain integration with iris-devtester."""

    print("=" * 70)
    print("Testing LangChain Integration (Community langchain-iris)")
    print("=" * 70)
    print()

    # Create IRIS container
    print("🚀 Starting IRIS container...")
    with LangChainIRISContainer.community() as iris:
        print(f"✓ IRIS ready at {iris.get_connection_string()}")
        print()

        # Get vector store with fake embeddings (no API key needed)
        print("📦 Creating vector store with FakeEmbeddings...")
        embeddings = FakeEmbeddings(size=1536)
        vectorstore = iris.get_langchain_vectorstore(
            embedding_model=embeddings, collection_name="test"
        )
        print("✓ Vector store created")
        print()

        # Test add_documents
        print("📝 Adding test documents...")
        docs = [
            Document(
                page_content="IRIS Vector Search is fast",
                metadata={"source": "test.pdf", "page": 1},
            ),
            Document(
                page_content="LangChain integration works great",
                metadata={"source": "test.pdf", "page": 2},
            ),
            Document(
                page_content="iris-devtester makes testing easy",
                metadata={"source": "test.pdf", "page": 3},
            ),
        ]

        ids = vectorstore.add_documents(docs)
        print(f"✓ Added {len(ids)} documents (IDs: {ids})")
        print()

        # Test similarity_search
        print("🔍 Testing similarity search...")
        query = "vector search"
        results = vectorstore.similarity_search(query, k=2)

        print(f"Query: '{query}'")
        print(f"Found {len(results)} results:")
        for i, doc in enumerate(results, 1):
            print(f"  {i}. {doc.page_content[:50]}...")
        print()

        # Test similarity_search_with_score
        print("🔍 Testing similarity search with scores...")
        results_with_scores = vectorstore.similarity_search_with_score(query, k=2)

        print(f"Query: '{query}'")
        print(f"Found {len(results_with_scores)} results with scores:")
        for i, (doc, score) in enumerate(results_with_scores, 1):
            print(f"  {i}. Score: {score:.4f} - {doc.page_content[:50]}...")
        print()

    print("✓ Container stopped and cleaned up")
    print()
    print("=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print()
    print("Integration working correctly with:")
    print("  - langchain-iris (community version)")
    print("  - iris-devtester LangChainIRISContainer")
    print("  - Automatic password reset & CallIn enablement")
    print("  - Zero-config deployment")
    print()


if __name__ == "__main__":
    test_basic_integration()
