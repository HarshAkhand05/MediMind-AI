import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec


load_dotenv()

# Debug: check if API key is loading
# print("Loaded Pinecone API Key:", os.getenv("PINECONE_API_KEY"))

api_key = os.getenv("PINECONE_API_KEY")
if not api_key:
    raise ValueError("❌ PINECONE_API_KEY is missing!")




INDEX_NAME = os.getenv("INDEX_NAME", "medstudy-assistant")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

def get_or_create_index():
    if not pc.has_index(INDEX_NAME):
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
        )
    return pc.Index(name=INDEX_NAME)

index = get_or_create_index()
