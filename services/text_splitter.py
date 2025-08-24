import re
from typing import List, Tuple

# services/text_splitter.py
def split_text(raw_text, chunk_size=1000, chunk_overlap=200):
    """
    Takes raw text string and splits into chunks.
    Returns [(chunk_id, chunk_text), ...]
    """
    chunks = []
    start = 0
    i = 0
    while start < len(raw_text):
        end = min(start + chunk_size, len(raw_text))
        chunk = raw_text[start:end]
        chunks.append((i, chunk.strip()))
        i += 1
        start += chunk_size - chunk_overlap
    return chunks
