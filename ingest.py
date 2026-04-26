"""
ingest.py — Scrape IXL Public Adjuster website and load into ChromaDB.

Usage:
    python ingest.py

Run this from the Render shell after deploy to populate the knowledge base.
"""

import os
import re
import time
import requests
import chromadb
from chromadb.config import Settings
from bs4 import BeautifulSoup
from voyageai import Client as VoyageClient

VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
CHROMA_PATH = os.environ.get("CHROMA_PATH", "/data/chroma_db")

voyage_client = VoyageClient(api_key=VOYAGE_API_KEY)

chroma_client = chromadb.PersistentClient(
    path=CHROMA_PATH,
    settings=Settings(anonymized_telemetry=False)
)
collection = chroma_client.get_or_create_collection(name="ixl")

# Pages to scrape
PAGES = [
    "https://ixlpublicadjuster.com/",
    "https://ixlpublicadjuster.com/about/",
    "https://ixlpublicadjuster.com/services/",
    "https://ixlpublicadjuster.com/faq/",
    "https://ixlpublicadjuster.com/contact/",
]

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
BATCH_SIZE = 128

def fetch_page_text(url):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; IXLBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "noscript", "header"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks

def embed_batch(texts):
    result = voyage_client.embed(texts, model="voyage-3")
    return result.embeddings

def ingest():
    all_chunks = []
    all_metas = []

    for url in PAGES:
        print(f"Fetching: {url}")
        try:
            text = fetch_page_text(url)
            chunks = chunk_text(text)
            for chunk in chunks:
                all_chunks.append(chunk)
                all_metas.append({"source": url})
            print(f"  → {len(chunks)} chunks")
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(1)

    print(f"\nTotal chunks: {len(all_chunks)}")

    # Clear existing scraped docs (keep admin-added ones)
    try:
        existing = collection.get(where={"source": {"$ne": "admin"}})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            print(f"Cleared {len(existing['ids'])} existing scraped docs")
    except Exception as e:
        print(f"Clear step skipped: {e}")

    # Embed and store in batches
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch_docs = all_chunks[i:i+BATCH_SIZE]
        batch_metas = all_metas[i:i+BATCH_SIZE]
        batch_ids = [f"doc_{i+j}" for j in range(len(batch_docs))]
        batch_embs = embed_batch(batch_docs)
        collection.add(
            documents=batch_docs,
            embeddings=batch_embs,
            ids=batch_ids,
            metadatas=batch_metas
        )
        print(f"  Stored batch {i//BATCH_SIZE + 1} ({len(batch_docs)} docs)")

    print("\nIngestion complete.")

if __name__ == "__main__":
    ingest()