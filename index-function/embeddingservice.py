from openai import AzureOpenAI

class EmbeddingService:
    def __init__(
            self,
            azureOpenAI : AzureOpenAI
        ):
        self.azureOpenAI = azureOpenAI

    def get_embedding(self, text, model="text-embedding-ada-002"):
        response = self.azureOpenAI.embeddings.create(
            input=[text],
            model=model
        )
        return response.data[0].embedding
    