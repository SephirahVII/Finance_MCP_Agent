from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from invesagent_rag.config import RagConfig


class Embedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, query: str) -> list[float]:
        ...


@dataclass
class OpenAIEmbedder:
    model: str = "text-embedding-3-small"

    def __post_init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for RAG embeddings.")
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install openai to use OpenAI embeddings.") from exc
        self.client = OpenAI(api_key=api_key)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


@dataclass
class LocalTransformerEmbedder:
    model: str = "BAAI/bge-m3"
    device: str | None = None
    local_files_only: bool = False
    batch_size: int = 4

    def __post_init__(self) -> None:
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Install torch, transformers, and sentencepiece to use local RAG embeddings."
            ) from exc
        self.torch = torch
        self.device_name = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model,
            trust_remote_code=True,
            local_files_only=self.local_files_only,
        )
        self.encoder = AutoModel.from_pretrained(
            self.model,
            trust_remote_code=True,
            local_files_only=self.local_files_only,
        ).to(self.device_name)
        self.encoder.eval()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = []
        for start in range(0, len(texts), self.batch_size):
            batch_texts = texts[start : start + self.batch_size]
            batch = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            batch = {key: value.to(self.device_name) for key, value in batch.items()}
            with self.torch.no_grad():
                output = self.encoder(**batch)
                embedding = output.last_hidden_state[:, 0]
                embedding = self.torch.nn.functional.normalize(embedding, p=2, dim=1)
            vectors.extend(embedding.cpu().float().tolist())
        return vectors

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


def build_embedder(config: RagConfig) -> Embedder:
    if config.embedding_provider == "local":
        return LocalTransformerEmbedder(
            model=config.embedding_model,
            device=config.embedding_device,
            local_files_only=config.embedding_local_files_only,
            batch_size=config.embedding_batch_size,
        )
    if config.embedding_provider == "openai":
        return OpenAIEmbedder(model=config.embedding_model)
    raise ValueError(
        "Unsupported RAG_EMBEDDING_PROVIDER: "
        f"{config.embedding_provider}. Use 'local' or 'openai'."
    )
