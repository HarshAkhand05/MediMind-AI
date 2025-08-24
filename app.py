import os
import uuid
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# --- Services ---
from services.parsers import extract_text
from services.text_splitter import split_text
from services.embeddings import embed_texts, answer_with_context
from services.pinecone_client import index
from services.retriever import query_chunks   # ✅ FIX: added import

# --- Setup ---
load_dotenv()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {".pdf", ".docx", ".txt", ".md"}

app = Flask(__name__)
CORS(app)


@app.get("/health")
def health():
    return {"ok": True}


def _allowed(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXT


# ------------------ UPLOAD ------------------
@app.post("/upload")
def upload():
    student_id = request.form.get("student_id")
    f = request.files.get("file")
    if not student_id or not f:
        return jsonify({"error": "student_id and file are required"}), 400

    filename = secure_filename(f.filename)
    file_id = str(uuid.uuid4())
    saved_path = os.path.join(UPLOAD_DIR, f"{file_id}_{filename}")
    f.save(saved_path)

    vectors_to_upsert = []
    chunk_counter = 0

    # ✅ Stream pages instead of one big string
    for page_text in extract_text(saved_path):
        page_chunks = split_text(page_text, chunk_size=1000, chunk_overlap=200)
        texts = [c[1] for c in page_chunks]
        vectors = embed_texts(texts, task_type="retrieval_document")   # ✅ FIX: lowercase

        for (chunk_id, text), vec in zip(page_chunks, vectors):
            vectors_to_upsert.append({
                "id": f"{file_id}-{chunk_counter}",
                "values": vec,
                "metadata": {
                    "doc_id": file_id,
                    "filename": filename,
                    "chunk_id": chunk_counter,
                    "text": text[:1200]
                }
            })
            chunk_counter += 1

    # ✅ Upload in one go
    if vectors_to_upsert:
        index.upsert(vectors=vectors_to_upsert, namespace=student_id)

    return jsonify({
        "ok": True,
        "doc_id": file_id,
        "num_chunks": chunk_counter,
        "filename": filename
    }), 200


# ------------------ ASK ------------------
@app.post("/ask")
def ask():
    """
    JSON:
      {
        "student_id": "...",
        "question": "What is the mechanism of action of ...?",
        "top_k": 6
      }
    """
    body = request.get_json(force=True)
    student_id = body.get("student_id")
    question = body.get("question", "").strip()
    top_k = int(body.get("top_k", 6))

    if not student_id or not question:
        return jsonify({"error": "student_id and question are required"}), 400

    # Retrieve relevant chunks from student's namespace
    result = query_chunks(student_id, question, top_k=top_k)
    matches = result.get("matches", [])

    if not matches:
        return jsonify({
            "answer": "I couldn’t find this in your notes.",
            "context_used": [],
        })

    # Build context block
    context_blocks = []
    for m in matches:
        meta = m["metadata"]
        snippet = meta.get("text", "")
        context_blocks.append(
            f"[chunk {meta.get('chunk_id')} from {meta.get('filename')}] {snippet}"
        )
    context_str = "\n\n".join(context_blocks)

    answer = answer_with_context(question, context_str, temperature=0.2)

    # Return answer + citations (doc_id/chunk_id + score)
    citations = [{
        "doc_id": m["metadata"].get("doc_id"),
        "filename": m["metadata"].get("filename"),
        "chunk_id": m["metadata"].get("chunk_id"),
        "score": m.get("score")
    } for m in matches]

    return jsonify({
        "answer": answer,
        "context_used": citations
    })


# ------------------ SUMMARIZE ------------------
@app.post("/summarize")
def summarize():
    """
    JSON:
      {
        "student_id": "...",
        "topic": "Renin-angiotensin-aldosterone system",
        "top_k": 12
      }
    """
    body = request.get_json(force=True)
    student_id = body.get("student_id")
    topic = body.get("topic", "").strip()
    top_k = int(body.get("top_k", 12))

    if not student_id or not topic:
        return jsonify({"error": "student_id and topic are required"}), 400

    result = query_chunks(student_id, topic, top_k=top_k)
    matches = result.get("matches", [])

    if not matches:
        return jsonify({"summary": "No relevant notes found to summarize."})

    parts = []
    for m in matches:
        meta = m["metadata"]
        parts.append(
            f"[chunk {meta.get('chunk_id')} from {meta.get('filename')}] {meta.get('text','')}"
        )
    ctx = "\n\n".join(parts)

    prompt = (
        f"Summarize the topic: {topic} using ONLY the context below. "
        f"Produce a concise, exam-oriented summary with bullet points and key definitions."
    )
    summary = answer_with_context(prompt, ctx, temperature=0.2)

    return jsonify({
        "topic": topic,
        "summary": summary
    })


# ------------------ FLASHCARDS ------------------
@app.post("/flashcards")
def flashcards():
    try:
        body = request.get_json(force=True)
        student_id = body.get("student_id")
        topic = (body.get("topic") or "").strip()
        top_k = int(body.get("top_k", 10))

        if not student_id or not topic:
            return jsonify({"error": "student_id and topic are required"}), 400

        from services.retriever import query_chunks
        result = query_chunks(student_id, topic, top_k=top_k)
        matches = result.get("matches", [])

        if matches:
            ctx = "\n\n".join([m["metadata"].get("text", "") for m in matches])
        else:
            # 🔥 fallback if retriever returns nothing
            ctx = f"General notes about {topic}"

        # --- Flashcard generation prompt ---
        prompt = (
            f"Generate 6-8 flashcards for medical exam preparation about **{topic}**. "
            f"If context is available, use ONLY that. If not, use general medical knowledge. "
            f"Each flashcard must be a JSON object with 'question' and 'answer'. "
            f"Return ONLY a valid JSON list. Example:\n"
            f'[{{"question": "What is X?", "answer": "Y"}}]\n\n'
            f"Context:\n{ctx}"
        )

        response = answer_with_context(prompt, ctx, temperature=0.3)

        # Try parsing JSON
        try:
            flashcards = json.loads(response)
        except Exception:
            # Fallback: extract Q&A style manually
            flashcards = []
            for line in response.split("\n"):
                if "?" in line:
                    flashcards.append({"question": line.strip(), "answer": ""})

        return jsonify({"flashcards": flashcards})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------ MAIN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055, debug=True)
