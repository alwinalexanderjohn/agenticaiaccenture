"""
EcoHome Energy Advisor — RAG Pipeline Setup Script
Run this directly: python setup_rag.py
Embeds all .txt files from data/documents/ into ChromaDB.
Requires OPENAI_API_KEY in .env
"""

import os, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DOCS_DIR        = os.path.join(os.path.dirname(__file__), "data", "documents")
VECTORSTORE_DIR = os.path.join(os.path.dirname(__file__), "data", "vectorstore")
COLLECTION_NAME = "energy_tips"
CHUNK_SIZE      = 800
CHUNK_OVERLAP   = 100


def setup_rag():
    import chromadb
    from langchain_openai import OpenAIEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    os.makedirs(VECTORSTORE_DIR, exist_ok=True)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Copy .env.example to .env and fill in your key.")

    # ── Load documents ────────────────────────────────────────────────────────
    docs = []
    for txt_file in sorted(Path(DOCS_DIR).glob("*.txt")):
        content = txt_file.read_text(encoding="utf-8")
        first_line = content.split("\n")[0]
        topic = first_line.replace("TOPIC:", "").strip() if "TOPIC:" in first_line else txt_file.stem
        docs.append({"content": content, "source": txt_file.name, "topic": topic})
        print(f"  Loaded: {txt_file.name}  ({len(content):,} chars)")

    print(f"\n  ✅ {len(docs)} documents loaded")

    # ── Chunk ────────────────────────────────────────────────────────────────
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks, metadatas, ids = [], [], []
    for di, doc in enumerate(docs):
        for ci, chunk in enumerate(splitter.split_text(doc["content"])):
            chunks.append(chunk)
            metadatas.append({"source": doc["source"], "topic": doc["topic"], "chunk_idx": ci})
            ids.append(f"doc{di}_chunk{ci}")

    print(f"  ✅ {len(chunks)} chunks created  (avg {sum(len(c) for c in chunks)//len(chunks)} chars)")

    # ── Embed ────────────────────────────────────────────────────────────────
    print("\n  Computing embeddings (30-60 s)...")
    embed_model = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=api_key)
    embeddings  = embed_model.embed_documents(chunks)
    print(f"  ✅ {len(embeddings)} vectors  (dim={len(embeddings[0])})")

    # ── Store in ChromaDB ────────────────────────────────────────────────────
    client = chromadb.PersistentClient(path=VECTORSTORE_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
        print("  (Deleted previous collection)")
    except Exception:
        pass

    collection = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    BATCH = 500
    for i in range(0, len(chunks), BATCH):
        collection.add(
            documents=chunks[i:i+BATCH],
            embeddings=embeddings[i:i+BATCH],
            metadatas=metadatas[i:i+BATCH],
            ids=ids[i:i+BATCH],
        )

    print(f"  ✅ {collection.count()} chunks stored in ChromaDB at: {VECTORSTORE_DIR}")

    # ── Quick sanity check ───────────────────────────────────────────────────
    print("\n  Quick retrieval test...")
    q_emb = embed_model.embed_query("best time to charge electric vehicle")
    res = collection.query(query_embeddings=[q_emb], n_results=2,
                           include=["documents", "metadatas", "distances"])
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        print(f"    [{meta['source']}] score={1-dist:.3f}  → {doc[:80].strip()}...")

    print("\n🎉 RAG pipeline ready!")


if __name__ == "__main__":
    print("EcoHome — Setting up RAG pipeline...")
    setup_rag()
