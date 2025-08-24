import os
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBED_MODEL = os.getenv("EMBED_MODEL", "models/embedding-001")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


def embed_texts(texts, task_type="retrieval_document"):
    """
    Embed a list of texts and return their vectors.
    task_type: 'retrieval_document' for chunks, 'retrieval_query' for user queries.
    """
    embeddings = []
    for t in texts:
        resp = genai.embed_content(
            model=EMBED_MODEL,
            content=t,
            task_type=task_type,
            output_dimensionality=EMBED_DIM,
        )
        embeddings.append(resp["embedding"])  # resp is a dict with "embedding" key
    return embeddings


def answer_with_context(prompt, context, temperature=0.2, model="gemini-1.5-flash"):
    """
    Ask Gemini a question with retrieved context.
    """
    sys = (
       "You are a helpful medical study assistant. Answer ONLY from the provided context. "
         "If the answer cannot be found, say 'I couldn’t find this in your notes.' "
        "Do NOT mention chunk numbers or file names in the answer."
    )

    full_prompt = (
        f"{sys}\n\n"
        f"### Context\n{context}\n\n"
        f"### Question\n{prompt}\n\n"
        f"### Instructions\n- Keep it accurate.\n- Prefer bullet points.\n"
    )

    model_obj = genai.GenerativeModel(model)
    r = model_obj.generate_content(full_prompt, generation_config={"temperature": temperature})
    return r.text or ""
