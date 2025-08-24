import json
import streamlit as st
import requests

# Backend base URL
BASE_URL = "http://127.0.0.1:5055"

# Streamlit Page Config
st.set_page_config(page_title="MediMind Chatbot", page_icon="🧠", layout="wide")

# --- Custom Styling ---
st.markdown("""
    <style>
    .main {
        background: #f8f9fa;
    }
    .stButton>button {
        background-color: #4CAF50;
        color:white;
        border-radius: 10px;
        padding: 10px 20px;
        font-size: 16px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .block-container {
        padding-top: 1rem;
    }
    .flashcard {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        font-size: 18px;
        color: #333333;
    }
    .flashcard-question {
        font-weight: bold;
        color: #d9534f;
        margin-bottom: 10px;
    }
    .flashcard-answer {
        font-weight: normal;
        color: #5cb85c;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Title ---
st.title("🧠 MediMind - Student Medical Chatbot")
st.markdown("Upload your notes, ask questions, and get exam-focused summaries & flashcards!")

# --- Sidebar ---
st.sidebar.header("⚙️ Settings")
student_id = st.sidebar.text_input("🆔 Student ID", value="123")
st.sidebar.info("Use your Student ID to keep documents separate.")

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📂 Upload Notes", "❓ Ask Questions", "📝 Summarize", "🎴 Flashcards"])


# ================== TAB 1: UPLOAD ==================
with tab1:
    st.subheader("📂 Upload your Study Notes")
    uploaded_file = st.file_uploader("Upload PDF, DOCX, TXT, or MD", type=["pdf", "docx", "txt", "md"])

    if uploaded_file is not None:
        if st.button("🚀 Upload File"):
            with st.spinner("📤 Uploading and processing your document..."):
                files = {"file": (uploaded_file.name, uploaded_file, "application/octet-stream")}
                data = {"student_id": student_id}
                try:
                    res = requests.post(f"{BASE_URL}/upload", files=files, data=data)
                    if res.status_code == 200:
                        result = res.json()
                        st.success(f"✅ Uploaded: **{result['filename']}** with **{result['num_chunks']} chunks**")
                    else:
                        st.error(f"❌ Upload failed: {res.text}")
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")


# ================== TAB 2: ASK ==================
with tab2:
    st.subheader("❓ Ask a Question from Your Notes")
    question = st.text_area("💬 Enter your question here", height=100,
                            placeholder="E.g., What is the mechanism of action of aspirin?")
    
    if st.button("🔍 Get Answer"):
        if not question.strip():
            st.warning("⚠️ Please enter a question.")
        else:
            with st.spinner("🤔 Thinking..."):
                payload = {"student_id": student_id, "question": question, "top_k": 6}
                try:
                    res = requests.post(f"{BASE_URL}/ask", json=payload)
                    if res.status_code == 200:
                        result = res.json()
                        st.success("✅ Answer received!")
                        st.markdown("### 📌 Answer:")
                        st.info(result["answer"])

                        with st.expander("📚 Show Context Chunks Used"):
                            st.json(result["context_used"])
                    else:
                        st.error(f"❌ Failed: {res.text}")
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")


# ================== TAB 3: SUMMARIZE ==================
with tab3:
    st.subheader("📝 Summarize a Topic from Notes")
    topic = st.text_input("📖 Enter a topic to summarize",
                          placeholder="E.g., Renin-angiotensin-aldosterone system")
    
    if st.button("🖊️ Summarize Notes"):
        if not topic.strip():
            st.warning("⚠️ Please enter a topic.")
        else:
            with st.spinner("📝 Summarizing..."):
                payload = {"student_id": student_id, "topic": topic, "top_k": 12}
                try:
                    res = requests.post(f"{BASE_URL}/summarize", json=payload)
                    if res.status_code == 200:
                        result = res.json()
                        st.success("✅ Summary generated!")
                        st.markdown(f"### 📌 Summary of *{topic}*")
                        st.write(result["summary"])
                    else:
                        st.error(f"❌ Failed: {res.text}")
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")


# ---------- Helper ----------
def normalize_cards(raw_cards):
    """Convert backend flashcards into clean dicts with 'question' and 'answer'."""
    cards = []
    for item in raw_cards:
        if isinstance(item, dict):
            q, a = item.get("question", ""), item.get("answer", "")
        elif isinstance(item, str):
            try:
                obj = json.loads(item)
                if isinstance(obj, dict):
                    q, a = obj.get("question", ""), obj.get("answer", "")
                else:
                    q, a = item, ""
            except:
                q, a = item, ""
        else:
            q, a = str(item), ""
        cards.append({"question": q, "answer": a})
    return cards


# ================== TAB 4: FLASHCARDS ==================
with tab4:
    st.subheader("🎴 Generate Flashcards for Revision")
    topic = st.text_input("📖 Enter a topic for flashcards", placeholder="e.g., Diabetes Mellitus")

    # --- Request flashcards from backend ---
    if st.button("Generate Flashcards"):
        if not topic.strip():
            st.warning("⚠️ Please enter a topic.")
        else:
            with st.spinner("🎴 Creating flashcards..."):
                payload = {"student_id": student_id, "topic": topic, "top_k": 10}
                res = requests.post(f"{BASE_URL}/flashcards", json=payload)
                if res.status_code == 200:
                    result = res.json()

                    # ✅ FIX: clean JSON into question/answer
                    def normalize_cards(raw_cards):
                        cards = []
                        for item in raw_cards:
                            try:
                                if isinstance(item, str):  # if backend gave JSON string
                                    item = json.loads(item)
                                if isinstance(item, dict):
                                    cards.append({
                                        "question": item.get("question", ""),
                                        "answer": item.get("answer", "")
                                    })
                            except:
                                pass
                        return cards

                    st.session_state["flashcards"] = normalize_cards(result.get("flashcards", []))
                    st.session_state["index"] = 0
                    st.session_state["show_answer"] = False
                else:
                    st.error(f"❌ Failed: {res.text}")

    # --- Display flashcards ---
    if "flashcards" in st.session_state and st.session_state["flashcards"]:
        cards = st.session_state["flashcards"]
        idx = st.session_state.get("index", 0)
        card = cards[idx]

        st.markdown(f"### 🃏 Flashcard {idx+1} of {len(cards)}")

        # ✅ Styled card box
        st.markdown("<div style='background:white;padding:20px;border-radius:12px;"
                    "box-shadow:0 4px 10px rgba(0,0,0,0.2);'>", unsafe_allow_html=True)

        st.markdown(f"**❓ Question:** {card['question']}")
        if st.session_state.get("show_answer", False):
            st.markdown(f"**✅ Answer:** {card['answer']}")

        st.markdown("</div>", unsafe_allow_html=True)

        # --- Controls ---
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("⬅️ Previous"):
                st.session_state["index"] = (idx - 1) % len(cards)
                st.session_state["show_answer"] = False
                st.rerun()
        with col2:
            if st.button("🔄 Flip Card"):
                st.session_state["show_answer"] = not st.session_state["show_answer"]
                st.rerun()
        with col3:
            if st.button("➡️ Next"):
                st.session_state["index"] = (idx + 1) % len(cards)
                st.session_state["show_answer"] = False
                st.rerun()

