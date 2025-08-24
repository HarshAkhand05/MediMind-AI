from typing import List, Dict
from .pinecone_client import index
from .embeddings import embed_texts

def query_chunks(student_ns: str, question: str, top_k: int = 6) -> Dict:
    qvec = embed_texts([question], task_type="RETRIEVAL_QUERY")[0]
    # We keep each student's data isolated via `namespace=student_ns`
    result = index.query(
        vector=qvec,
        top_k=top_k,
        include_values=False,
        include_metadata=True,
        namespace=student_ns
    )
    return result
