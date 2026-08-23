
# Website Scraping RAG Application

## 🏗️ Architecture Explanation
WebRAG Studio follows an end-to-end RAG architecture where website content is collected and converted into a searchable knowledge base.
The website is crawled, cleaned, split into chunks, converted into embeddings, and stored in ChromaDB.
When a user asks a question, the system performs semantic search to retrieve the most relevant chunks.
These chunks are given as context to the Qwen3:8B LLM running through Ollama to generate a grounded answer.
Finally, Streamlit displays the retrieved information and generated answer to the user.

## 🏗️ Architecture

![WebRAG Studio Architecture](https://github.com/user-attachments/assets/1beddca0-13a2-4229-811c-4efbd27e36a1)

