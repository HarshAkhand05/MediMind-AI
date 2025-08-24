import os
from pypdf import PdfReader
import docx

def extract_text(file_path: str):
    """
    Yields text chunk by chunk instead of loading entire file into memory.
    For PDFs → yields per page.
    For DOCX → yields per paragraph.
    For TXT/MD → yields per line block.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        reader = PdfReader(file_path)
        for page in reader.pages:
            yield page.extract_text() or ""

    elif ext == ".docx":
        d = docx.Document(file_path)
        for p in d.paragraphs:
            if p.text.strip():
                yield p.text

    elif ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            buffer = []
            for line in f:
                buffer.append(line.strip())
                # yield in chunks of ~100 lines (to avoid memory spike)
                if len(buffer) >= 100:
                    yield "\n".join(buffer)
                    buffer = []
            if buffer:
                yield "\n".join(buffer)

    else:
        raise ValueError(f"Unsupported file type: {ext}")
