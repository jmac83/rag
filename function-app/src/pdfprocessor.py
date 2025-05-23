import uuid
import io
import fitz
from transformers import GPT2TokenizerFast

class PDFProcessor:

    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50

    def __init__(
            self,
            tokenizer : GPT2TokenizerFast
        ):
        self.tokenizer = tokenizer

    def __extract_text_from_pdf(self, pdf_stream : io.BytesIO):
        doc = fitz.open(stream=pdf_stream.getvalue(), filetype="pdf")
        full_text = []
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text:
                full_text.append((page_num + 1, text.strip()))
        return full_text

    def __chunk_text(self, text):
        tokens = self.tokenizer.encode(text)
        chunks = []
        start = 0
        while start < len(tokens):
            end = start + self.CHUNK_SIZE
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text.strip())
            start += self.CHUNK_SIZE - self.CHUNK_OVERLAP
        return chunks

    def process_pdf_to_chunks(self, pdf_stream : io.BytesIO):
        page_texts = self.__extract_text_from_pdf(pdf_stream)
        chunk_records = []

        for page_num, page_text in page_texts:
            chunks = self.__chunk_text(page_text)
            for i, chunk in enumerate(chunks):
                record = {
                    "id": str(uuid.uuid4()),
                    "content": chunk,
                    "metadata": {
                        "source_page": page_num,
                        "chunk_index": i
                    }
                }
                chunk_records.append(record)

        return chunk_records
    