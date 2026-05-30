from __future__ import annotations

__all__ = ["RagRetriever"]


def __getattr__(name: str):
    if name == "RagRetriever":
        from invesagent_rag.retriever import RagRetriever

        return RagRetriever
    raise AttributeError(name)
