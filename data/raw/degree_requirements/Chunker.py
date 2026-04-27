#libaries
import tiktoken
import json
import requests
from bs4 import BeautifulSoup
from datetime import date
import os
import time

enc = tiktoken.get_encoding("cl100k_base")

def save_documents(documents, category):
    folder = f"data/chunks/{category}"
    os.makedirs(folder, exist_ok=True)
    filepath = f"{folder}/{category}.json"

    with open(filepath, "w") as f:
        json.dump(documents, f, indent=2)

    print(f"\nSaved {len(documents)} documents to {filepath}")


def load_documents(filepath):
    with open(filepath, "r") as f:
        return json.load(f)


def process_category(category):
    input_path = f"data/raw/{category}/{category}.json"

    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    print(f"\nProcessing category: {category}")

    documents = load_documents(input_path)
    chunked_docs = chunk_documents(documents)

    save_documents(chunked_docs, category)


def chunk_text_tokens(text, max_tokens=300, overlap=50):
    tokens = enc.encode(text)
    chunks = []

    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]

        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text)

        start += max_tokens - overlap

    return chunks


def chunk_documents(documents):
    chunked_docs = []

    for doc in documents:
        chunks = chunk_text_tokens(doc["text"])

        for i, chunk in enumerate(chunks):
            chunked_docs.append({
                "chunk_text": chunk,
                "source": doc["source"],
                "title": doc["title"],
                "college": doc["college"],
                "category": doc["category"],
                "section": doc["section"],
                "chunk_id": i,
                "token_count": len(enc.encode(chunk))
            })

    return chunked_docs


if __name__ == "__main__":
    categories = [
        "registration_enrollment",
    ]

    for category in categories:
        process_category(category)
