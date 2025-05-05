from langchain_core.embeddings import Embeddings
import requests

class RemoteOllamaEmbeddings(Embeddings):
    def __init__(self, base_url: str, model: str = "nomic-embed-text"):
        self.base_url = base_url
        self.model = model

    def embed_documents(self, texts):
        return [self._embed(text) for text in texts]

    def embed_query(self, text):
        return self._embed(text)

    def _embed(self, text):
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
            timeout=60
        )
        response.raise_for_status()
        return response.json()["embedding"]
