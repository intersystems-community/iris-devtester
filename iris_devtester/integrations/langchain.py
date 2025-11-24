"""
LangChain integration for iris-devtester.

Provides zero-config testing infrastructure for IRIS-based LangChain applications.
Compatible with InterSystems' official langchain-iris package.

Example:
    >>> from iris_devtester.integrations.langchain import LangChainIRISContainer
    >>> from langchain_openai import OpenAIEmbeddings
    >>>
    >>> with LangChainIRISContainer.community() as iris:
    ...     vectorstore = iris.get_langchain_vectorstore(OpenAIEmbeddings())
    ...     # Build your RAG app...
"""

import logging
from typing import Any, Optional

from iris_devtester.containers.iris_container import IRISContainer

logger = logging.getLogger(__name__)


class LangChainIRISContainer(IRISContainer):
    """
    IRISContainer optimized for LangChain applications.

    This class extends IRISContainer with convenience methods for LangChain
    integration, making it the standard testcontainers layer for IRIS-based
    AI applications.

    Compatible with:
    - InterSystems official langchain-iris package (coming soon)
    - Community langchain-iris (CaretDev)
    - iris-vector-rag framework
    - Custom LangChain applications

    Features:
    - Zero-config vector store setup
    - Automatic password reset & CallIn enablement
    - Developer experience parity with PostgreSQL/testcontainers-postgresql
    - Production-ready defaults

    Example:
        >>> from iris_devtester.integrations.langchain import LangChainIRISContainer
        >>> from langchain_openai import OpenAIEmbeddings
        >>>
        >>> # Zero-config setup (matches testcontainers-postgresql DX)
        >>> with LangChainIRISContainer.community() as iris:
        ...     vectorstore = iris.get_langchain_vectorstore(OpenAIEmbeddings())
        ...
        ...     # Add documents
        ...     docs = [Document(page_content="...", metadata={...})]
        ...     vectorstore.add_documents(docs)
        ...
        ...     # Search
        ...     results = vectorstore.similarity_search("query", k=5)
    """

    def get_langchain_vectorstore(
        self,
        embedding_model: Any,
        collection_name: str = "langchain",
        **kwargs: Any,
    ):
        """
        Get pre-configured LangChain vector store.

        This method provides zero-config access to an IRIS vector store that
        follows the standard LangChain VectorStore interface. All connection
        management (password reset, CallIn enablement) is handled automatically.

        Args:
            embedding_model: LangChain embedding model (e.g., OpenAIEmbeddings())
            collection_name: Name of the vector store collection (default: "langchain")
            **kwargs: Additional arguments passed to IRISVectorStore

        Returns:
            IRISVectorStore instance ready to use

        Raises:
            ImportError: If langchain-iris is not installed
            ConnectionError: If IRIS connection fails (with remediation guidance)

        Example:
            >>> from langchain_openai import OpenAIEmbeddings
            >>> from langchain.schema import Document
            >>>
            >>> with LangChainIRISContainer.community() as iris:
            ...     # Get vector store (zero-config)
            ...     vectorstore = iris.get_langchain_vectorstore(OpenAIEmbeddings())
            ...
            ...     # Load documents
            ...     docs = [
            ...         Document(
            ...             page_content="IRIS Vector Search uses native VECTOR datatype",
            ...             metadata={"source": "docs.pdf", "page": 1}
            ...         )
            ...     ]
            ...     vectorstore.add_documents(docs)
            ...
            ...     # Semantic search
            ...     results = vectorstore.similarity_search(
            ...         "What is IRIS Vector Search?",
            ...         k=5
            ...     )
            ...     for doc in results:
            ...         print(doc.page_content)

        Note:
            This method works with both the official InterSystems langchain-iris
            package (coming soon) and the community version (CaretDev). The API
            is identical, providing a smooth migration path.
        """
        try:
            from langchain_iris.vectorstores import IRISVector
        except ImportError as e:
            raise ImportError(
                "langchain-iris is not installed\n"
                "\n"
                "What went wrong:\n"
                "  The langchain-iris package is required for LangChain integration.\n"
                "\n"
                "How to fix it:\n"
                "  1. Install langchain-iris:\n"
                "     pip install langchain-iris\n"
                "  \n"
                "  2. Or install with all iris-devtester features:\n"
                "     pip install iris-devtester[langchain,all]\n"
                "\n"
                "Documentation:\n"
                "  - langchain-iris: https://pypi.org/project/langchain-iris/\n"
                "  - iris-devtester: https://github.com/intersystems-community/iris-devtester\n"
            ) from e

        # Get connection string with auto-remediation (password reset, CallIn, etc.)
        connection_string = self.get_connection_string()

        logger.info(
            f"Creating LangChain vector store '{collection_name}' with IRIS at {connection_string}"
        )

        # Create vector store with auto-configured connection
        vectorstore = IRISVector(
            embedding_function=embedding_model,
            connection_string=connection_string,
            collection_name=collection_name,
            **kwargs,
        )

        logger.info(f"✓ LangChain vector store '{collection_name}' ready")

        return vectorstore

    def get_connection_string(self) -> str:
        """
        Get IRIS connection string for LangChain.

        Returns connection string in format compatible with langchain-iris:
        iris://<username>:<password>@<host>:<port>/<namespace>

        Returns:
            IRIS connection string

        Example:
            >>> with LangChainIRISContainer.community() as iris:
            ...     conn_str = iris.get_connection_string()
            ...     print(conn_str)
            iris://SuperUser:SYS@localhost:52773/USER
        """
        # Ensure connection is ready (auto-remediation)
        _ = self.get_connection()

        # Get connection details
        host = self.get_container_host_ip()
        port = self.get_exposed_port(1972)  # SuperServer port
        username = getattr(self, "username", "SuperUser")
        password = getattr(self, "password", "SYS")
        namespace = getattr(self, "namespace", "USER")

        connection_string = (
            f"iris://{username}:{password}@{host}:{port}/{namespace}"
        )

        return connection_string

    def get_langchain_chat_history(
        self,
        session_id: str,
        **kwargs: Any,
    ):
        """
        Get pre-configured LangChain chat message history.

        Provides persistent chat history storage in IRIS for conversational
        AI applications. Messages are stored using IRIS globals for maximum
        performance.

        Args:
            session_id: Unique identifier for the chat session
            **kwargs: Additional arguments passed to IRISChatMessageHistory

        Returns:
            IRISChatMessageHistory instance

        Raises:
            ImportError: If langchain-iris chat history support is not available

        Example:
            >>> from langchain.memory import ConversationBufferMemory
            >>>
            >>> with LangChainIRISContainer.community() as iris:
            ...     # Get chat history for session
            ...     history = iris.get_langchain_chat_history("user-123")
            ...
            ...     # Use with LangChain memory
            ...     memory = ConversationBufferMemory(chat_memory=history)
            ...
            ...     # Messages persist in IRIS
            ...     memory.chat_memory.add_user_message("Hello!")
            ...     memory.chat_memory.add_ai_message("Hi! How can I help?")

        Note:
            Chat history functionality may not be available in all versions of
            langchain-iris. Check the package documentation for compatibility.
        """
        try:
            from langchain_iris import IRISChatMessageHistory
        except ImportError as e:
            raise ImportError(
                "langchain-iris chat history not available\n"
                "\n"
                "What went wrong:\n"
                "  IRISChatMessageHistory is not available in this version of langchain-iris.\n"
                "\n"
                "How to fix it:\n"
                "  1. Upgrade langchain-iris to the latest version:\n"
                "     pip install --upgrade langchain-iris\n"
                "  \n"
                "  2. Check if your version supports chat history:\n"
                "     pip show langchain-iris\n"
                "\n"
                "Note:\n"
                "  Chat history may be added in a future version of langchain-iris.\n"
                "  Check the package documentation for availability.\n"
            ) from e

        connection_string = self.get_connection_string()

        logger.info(
            f"Creating LangChain chat history for session '{session_id}'"
        )

        history = IRISChatMessageHistory(
            connection_string=connection_string,
            session_id=session_id,
            **kwargs,
        )

        logger.info(f"✓ Chat history ready for session '{session_id}'")

        return history

    @classmethod
    def for_rag_pipeline(
        cls,
        embedding_model: Any,
        namespace: Optional[str] = None,
        **container_kwargs: Any,
    ):
        """
        Create container optimized for RAG pipelines.

        This is a convenience factory method for RAG applications that need
        both vector store and document processing capabilities.

        Args:
            embedding_model: LangChain embedding model
            namespace: Optional IRIS namespace (default: USER)
            **container_kwargs: Additional arguments for IRISContainer

        Returns:
            Tuple of (IRISContainer, IRISVectorStore)

        Example:
            >>> from langchain_openai import OpenAIEmbeddings
            >>> from iris_vector_rag import create_pipeline
            >>>
            >>> embeddings = OpenAIEmbeddings()
            >>> iris, vectorstore = LangChainIRISContainer.for_rag_pipeline(embeddings)
            >>>
            >>> # Use with iris-vector-rag
            >>> pipeline = create_pipeline('basic', connection=iris.get_connection())
            >>> pipeline.load_documents([...])
            >>> result = pipeline.query("What is RAG?")
            >>>
            >>> # Cleanup
            >>> iris.stop()
        """
        # Create container with custom namespace if specified
        if namespace:
            container_kwargs["namespace"] = namespace

        container = cls.community(**container_kwargs)
        container.start()

        # Get vector store
        vectorstore = container.get_langchain_vectorstore(embedding_model)

        return container, vectorstore
