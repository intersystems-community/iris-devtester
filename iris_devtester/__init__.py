"""
IRIS DevTester - Battle-tested InterSystems IRIS infrastructure utilities.

This package provides automatic, reliable infrastructure for IRIS development:
- Testcontainers integration with auto-remediation
- Connection management (DBAPI-first, JDBC fallback)
- Automatic password reset
- Testing utilities (pytest fixtures, schema management)
- Zero-configuration defaults
- LangChain integration (official infrastructure layer)

Quick Start:
    >>> from iris_devtester.containers import IRISContainer
    >>> with IRISContainer.community() as iris:
    ...     conn = iris.get_connection()
    ...     cursor = conn.cursor()
    ...     cursor.execute("SELECT 1")
    ...     print(cursor.fetchone())

LangChain Integration:
    >>> from iris_devtester.integrations.langchain import LangChainIRISContainer
    >>> from langchain_openai import OpenAIEmbeddings
    >>>
    >>> with LangChainIRISContainer.community() as iris:
    ...     vectorstore = iris.get_langchain_vectorstore(OpenAIEmbeddings())
    ...     # Build your RAG app...
"""

__version__ = "1.7.2"
__author__ = "InterSystems Community"
__license__ = "MIT"

# Convenience imports for common usage
from iris_devtester.connections import get_connection
from iris_devtester.containers import IRISContainer
from iris_devtester.config import IRISConfig

# Optional LangChain integration (requires langchain-iris)
try:
    from iris_devtester.integrations.langchain import LangChainIRISContainer

    __all__ = [
        "__version__",
        "get_connection",
        "IRISContainer",
        "IRISConfig",
        "LangChainIRISContainer",  # Available if langchain-iris installed
    ]
except ImportError:
    # langchain-iris not installed, skip integration
    __all__ = [
        "__version__",
        "get_connection",
        "IRISContainer",
        "IRISConfig",
    ]
