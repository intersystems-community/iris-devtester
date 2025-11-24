"""
Example: LangChain integration with iris-devtester.

This example demonstrates zero-config LangChain development using iris-devtester
as the testcontainers infrastructure layer.

Requirements:
    pip install iris-devtester[all] langchain-iris langchain-openai

Usage:
    export OPENAI_API_KEY=your-key-here
    python examples/langchain_integration_example.py
"""

import os
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings

# NEW: Zero-config IRIS container for LangChain
from iris_devtester.integrations.langchain import LangChainIRISContainer


def main():
    """Demonstrate LangChain integration with iris-devtester."""

    print("=" * 70)
    print("LangChain + iris-devtester Integration Example")
    print("=" * 70)
    print()

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set")
        print("   This example requires OpenAI embeddings.")
        print("   Set your API key:")
        print("   export OPENAI_API_KEY=your-key-here")
        print()
        print("   Continuing with mock embeddings for demonstration...")
        print()
        use_real_embeddings = False
    else:
        use_real_embeddings = True

    # Create IRIS container (zero-config, automatic password reset & CallIn)
    print("🚀 Starting IRIS container...")
    with LangChainIRISContainer.community() as iris:
        print(f"✓ IRIS ready at {iris.get_connection_string()}")
        print()

        # Get LangChain vector store (zero-config)
        print("📦 Creating LangChain vector store...")
        if use_real_embeddings:
            embeddings = OpenAIEmbeddings()
        else:
            # Mock embeddings for demo purposes
            from langchain.embeddings import FakeEmbeddings

            embeddings = FakeEmbeddings(size=1536)

        vectorstore = iris.get_langchain_vectorstore(
            embedding_model=embeddings, collection_name="demo"
        )
        print("✓ Vector store ready")
        print()

        # Sample documents about IRIS Vector Search
        docs = [
            Document(
                page_content="InterSystems IRIS Vector Search provides a native VECTOR datatype for efficient similarity search.",
                metadata={"source": "iris_docs.pdf", "page": 1, "topic": "features"},
            ),
            Document(
                page_content="IRIS Vector Search leverages SIMD instructions for optimized chipset performance.",
                metadata={
                    "source": "iris_docs.pdf",
                    "page": 2,
                    "topic": "performance",
                },
            ),
            Document(
                page_content="LangChain integration with IRIS enables RAG applications with enterprise-grade vector storage.",
                metadata={
                    "source": "langchain_guide.pdf",
                    "page": 5,
                    "topic": "integration",
                },
            ),
            Document(
                page_content="IRIS supports hybrid search, combining vector similarity with SQL filters for precise retrieval.",
                metadata={
                    "source": "hybrid_search.pdf",
                    "page": 3,
                    "topic": "features",
                },
            ),
            Document(
                page_content="The iris-devtester package provides zero-config testcontainers infrastructure for IRIS development.",
                metadata={
                    "source": "testing_guide.pdf",
                    "page": 10,
                    "topic": "testing",
                },
            ),
        ]

        # Add documents to vector store
        print("📝 Adding documents to vector store...")
        ids = vectorstore.add_documents(docs)
        print(f"✓ Added {len(ids)} documents")
        print()

        # Semantic search example
        query = "How does IRIS optimize vector search performance?"
        print(f"🔍 Searching for: '{query}'")
        print()

        results = vectorstore.similarity_search(query, k=3)

        print(f"Found {len(results)} results:")
        print("-" * 70)
        for i, doc in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"Content: {doc.page_content}")
            print(f"Source: {doc.metadata.get('source', 'unknown')}")
            print(f"Page: {doc.metadata.get('page', 'unknown')}")
            print(f"Topic: {doc.metadata.get('topic', 'unknown')}")

        print()
        print("-" * 70)
        print()

        # Hybrid search example (vector + metadata filter)
        print("🔍 Hybrid search: performance-related documents only")
        print()

        # Filter for performance topic
        results_filtered = vectorstore.similarity_search(
            query, k=5, filter={"topic": "performance"}
        )

        print(f"Found {len(results_filtered)} results (filtered):")
        print("-" * 70)
        for i, doc in enumerate(results_filtered, 1):
            print(f"\nResult {i}:")
            print(f"Content: {doc.page_content}")
            print(f"Topic: {doc.metadata.get('topic')}")

        print()
        print("-" * 70)
        print()

    # Container automatically stopped and cleaned up
    print("✓ Container stopped and cleaned up")
    print()
    print("=" * 70)
    print("Example complete!")
    print()
    print("Key takeaways:")
    print("✅ Zero-config IRIS setup (no manual docker commands)")
    print("✅ Automatic password reset & CallIn enablement")
    print("✅ Standard LangChain VectorStore API")
    print("✅ Hybrid search (vector + SQL filters)")
    print("✅ Automatic cleanup")
    print()
    print("Next steps:")
    print("- Try with real OpenAI embeddings (set OPENAI_API_KEY)")
    print("- Integrate with iris-vector-rag for advanced RAG pipelines")
    print("- Build production AI applications with IRIS + LangChain")
    print("=" * 70)


if __name__ == "__main__":
    main()
