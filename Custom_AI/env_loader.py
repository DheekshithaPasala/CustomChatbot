from dotenv import load_dotenv
import os

load_dotenv()

print(" OpenAI Key Loaded:", bool(os.getenv("OPENAI_API_KEY")))
print(" Pinecone Key Loaded:", bool(os.getenv("PINECONE_API_KEY")))
