# InvesAgent RAG

`invesagent_rag` is a small Milvus-backed RAG package for historical text
corpora. The MVP supports government work reports and listed company annual
reports under:

```text
data/raw/macro_policy/
data/raw/company_report/
```

It can:

- infer metadata from report file paths and names;
- clean and chunk `.txt` reports;
- embed chunks with local sentence-transformers models;
- create and write to a Milvus collection;
- run command-line dense, BM25, and hybrid retrieval tests.

## Setup

Install the package from the workspace root:

```powershell
pip install -e invesagent_rag
```

Configure `.env` in the workspace root or `invesagent_rag/.env`:

```text
MILVUS_URI=http://127.0.0.1:19530
MILVUS_TOKEN=
RAG_COLLECTION=invesagent_policy_docs
RAG_EMBEDDING_PROVIDER=local
RAG_EMBEDDING_MODEL=BAAI/bge-m3
RAG_EMBEDDING_DIM=1024
RAG_EMBEDDING_DEVICE=cpu
RAG_EMBEDDING_LOCAL_FILES_ONLY=true
RAG_EMBEDDING_BATCH_SIZE=4
RAG_CHUNK_SIZE=900
RAG_CHUNK_OVERLAP=120
```

The default local embedding backend uses `BAAI/bge-m3`. The first run downloads
the model from Hugging Face unless the model is already cached or
`RAG_EMBEDDING_MODEL` points to a local model path.

## Commands

Initialize the Milvus collection:

```powershell
python -m invesagent_rag.cli init-store
```

Prepare metadata and parsed text without embeddings or Milvus:

```powershell
python -m invesagent_rag.cli prepare --limit 20
python -m invesagent_rag.cli prepare --source company_report --limit 5
```

Ingest a small sample first:

```powershell
python -m invesagent_rag.cli ingest --limit 20
python -m invesagent_rag.cli ingest --source company_report --limit 5
```

Ingest all reports:

```powershell
python -m invesagent_rag.cli ingest
python -m invesagent_rag.cli ingest --source company_report
```

Query:

```powershell
python -m invesagent_rag.cli query "地方政府如何支持新能源产业" --level prefecture --top-k 5
python -m invesagent_rag.cli query "财政政策和扩大内需" --level central --start-year 2020
python -m invesagent_rag.cli query "平安银行 风险管理 分红" --source company_report --symbol 000001 --mode bm25 --top-k 5
```
