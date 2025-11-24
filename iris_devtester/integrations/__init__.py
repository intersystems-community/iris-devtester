"""
Integration modules for iris-devtester with AI/ML frameworks.

This package provides seamless integration with popular AI/ML frameworks:
- LangChain: Vector stores, chat history, document loaders
- RAG frameworks: iris-vector-rag, LlamaIndex
- More integrations coming soon!
"""

from .langchain import LangChainIRISContainer

__all__ = ["LangChainIRISContainer"]
