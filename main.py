from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
import zipfile
import requests

from langchain_community.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

app = FastAPI()

# -- Configs --
GCS_ZIP_URL = "https://storage.googleapis.com/nsmr-chroma-store/chroma/chroma_db.zip"  # CHANGE THIS
VECTOR_DB_DIR = "vector_db"
VECTOR_DB_ZIP = "chroma_db.zip"
GROQ_API_KEY = "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"

# -- Step 1: Download + Extract Vector DB from GCS --
def download_and_extract_vector_db():
    if not os.path.exists(VECTOR_DB_DIR):
        print("Downloading vector DB from GCS...")
        r = requests.get(GCS_ZIP_URL)
        with open(VECTOR_DB_ZIP, "wb") as f:
            f.write(r.content)

        print("Extracting vector DB...")
        with zipfile.ZipFile(VECTOR_DB_ZIP, "r") as zip_ref:
            zip_ref.extractall(VECTOR_DB_DIR)

        print("Vector DB ready.")

# -- Step 2: Initialize Vector DB --
def load_vector_db():
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    return Chroma(persist_directory=VECTOR_DB_DIR, embedding_function=embeddings)

# -- Execute Initialization --
download_and_extract_vector_db()
vector_db = load_vector_db()
print("Vector database loaded successfully")

# -- Setup LLM Re-ranking --
llm = ChatGroq(groq_api_key=GROQ_API_KEY, model="llama3-8b-8192")
compressor = LLMChainExtractor.from_llm(llm)
compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=vector_db.as_retriever(search_kwargs={"k": 5})
)

# -- Prompt --
template = """Answer the question based ONLY on the following context:
{context}
Question: {question}
"""
prompt = ChatPromptTemplate.from_template(template)

# -- Request/Response Models --
class Query(BaseModel):
    question: str

class DocumentInfo(BaseModel):
    page: str
    link: str
    snippet: str

class Response(BaseModel):
    answer: str
    retrieved_documents: List[DocumentInfo]

# -- Endpoint --
@app.post("/ask", response_model=Response)
async def ask_question(query: Query):
    try:
        retrieved_docs = compression_retriever.get_relevant_documents(query.question)
        doc_info = [
            DocumentInfo(
                page=str(doc.metadata.get('page', 'N/A')),
                link=doc.metadata.get('source', 'N/A'),
                snippet=doc.page_content
            )
            for doc in retrieved_docs
        ]
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        formatted_prompt = prompt.format(context=context, question=query.question)
        response = llm.invoke(formatted_prompt)
        answer = response.content if hasattr(response, 'content') else str(response)
        return Response(answer=answer, retrieved_documents=doc_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
